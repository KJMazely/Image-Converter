"""Image conversion helpers used by both the command line and GUI."""

from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image, ImageOps

# Register optional HEIC support when the helper package is installed.
try:
    from pillow_heif import register_heif_opener
except ImportError:
    register_heif_opener = None
else:
    register_heif_opener()


# Output formats the converter can create.
SUPPORTED_FORMATS = {"jpg", "png"}

# HEIC-style files may need a fallback converter.
HEIC_FORMATS = {".heic", ".heif"}


def _find_heif_converter():
    # First check the bundled app folder, then fall back to the system path.
    app_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    bundled = app_root / "libheif_bin" / "heif-convert.exe"
    if bundled.is_file():
        return str(bundled)
    return shutil.which("heif-convert")


def _convert_heic_with_tool(source, output_path, target_format):
    # Use the local HEIC tool when Pillow cannot open HEIC directly.
    converter = _find_heif_converter()
    if not converter:
        raise RuntimeError(
            "HEIC support is not installed. Install pillow-heif or heif-convert and try again."
        )

    command = [converter, "--quiet"]
    if target_format == "jpg":
        # JPG quality is set high to avoid visible compression loss.
        command.extend(("--quality", "95"))
    else:
        # PNG compression keeps the file smaller without changing the image.
        command.extend(("--png-compression-level", "9"))
    command.extend((str(source), str(output_path)))

    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        message = f"Could not convert this HEIC image: {detail}" if detail else "Could not convert this HEIC image."
        raise RuntimeError(message)
    if not output_path.is_file():
        raise RuntimeError("The HEIC converter finished but did not create the output file.")
    return output_path


def image_file(file_name, new_format, output_dir=None):
    """Convert *file_name* to JPG or PNG and return the output path."""

    # Resolve and validate the selected image file.
    source = Path(file_name).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"'{source}' was not found.")

    # Normalize and validate the requested output format.
    target_format = new_format.lower().lstrip(".")
    if target_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format: {new_format}. Choose JPG or PNG.")

    # Use the chosen output folder, or save beside the original image.
    destination = Path(output_dir).expanduser().resolve() if output_dir else source.parent
    if not destination.is_dir():
        raise NotADirectoryError(f"'{destination}' is not a folder.")

    # Build the final output path.
    output_path = destination / f"{source.stem}.{target_format}"
    if output_path == source:
        raise ValueError("Choose a different output format from the source file.")

    # Fall back to heif-convert for HEIC/HEIF when Pillow lacks support.
    if source.suffix.lower() in HEIC_FORMATS and register_heif_opener is None:
        return _convert_heic_with_tool(source, output_path, target_format)

    try:
        with Image.open(source) as opened:
            # Apply camera rotation metadata before saving.
            image = ImageOps.exif_transpose(opened)
            if target_format == "jpg":
                # JPEG has no alpha channel; preserve the visible result on white.
                if image.mode in ("RGBA", "LA") or "transparency" in image.info:
                    rgba = image.convert("RGBA")
                    background = Image.new("RGB", rgba.size, "white")
                    background.paste(rgba, mask=rgba.getchannel("A"))
                    image = background
                else:
                    image = image.convert("RGB")
                image.save(output_path, "JPEG", quality=95, optimize=True)
            else:
                image.save(output_path, "PNG", optimize=True)
    except OSError as error:
        if source.suffix.lower() in HEIC_FORMATS and register_heif_opener is None:
            raise RuntimeError(
                "HEIC support is not installed. Run 'pip install -r requirements.txt' and try again."
            ) from error
        raise RuntimeError(f"Could not convert this image: {error}") from error
    return output_path
