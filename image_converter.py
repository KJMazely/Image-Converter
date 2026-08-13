"""A small desktop and command-line image converter."""


import argparse
import sys
import threading
import tkinter as tk
from pathlib import Path
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    HAS_TK = True
except ImportError:
    HAS_TK = False

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

# GUI requires both.
HAS_GUI = HAS_TK and HAS_DND


import convert


# Supported output formats shown in the combobox.
FORMATS = ("jpg", "png")

# Filter shown in the OS file-picker so only image types are listed.
IMAGE_TYPES = (
    ("Image files", "*.bmp *.gif *.heic *.heif *.ico *.jfif *.jpeg *.jpg *.png *.tif *.tiff *.webp"),
    ("All files", "*.*"),
)

def resource_path(relative: str) -> str:
    """Return the correct path whether running live or frozen by PyInstaller."""
    import sys
    base = getattr(sys, "_MEIPASS", Path(__file__).parent)
    return str(Path(base) / relative)


def apply_dark_mode(root: tk.Tk) -> None:
    """Restyle every ttk widget and the root window to a dark colour scheme."""

    # Color palette for dark mode.
    BG       = "#1e1e1e"   # window / frame background
    FG       = "#f0f0f0"   # primary text
    INPUT_BG = "#2d2d2d"   # entry / combobox background
    BTN_BG   = "#313131"   # button face
    BTN_ACT  = "#505050"   # button active / hover
    SELECT   = "#0078d4"   # accent (selection highlight)
    BORDER   = "#555555"   # widget border / trough

    # Apply background to the root window.
    root.configure(bg=BG)

    style = ttk.Style(root)
    style.theme_use("clam")

    # Base appearance of frame.
    style.configure("TFrame", background=BG)

    # Base appearance of label.
    style.configure("TLabel", background=BG, foreground=FG)

    # Base appearance of button.
    style.configure(
        "TButton",
        background=BTN_BG, foreground=FG,
        bordercolor=BORDER, darkcolor=BTN_BG, lightcolor=BTN_BG,
        relief="flat", padding=4,
    )
    # State-dependent overrides: hover, disabled.
    style.map(
        "TButton",
        background=[("active", BTN_ACT), ("disabled", BG)],
        foreground=[("disabled", BORDER)],
        bordercolor=[("active", SELECT)],
    )

    # Base appearance; insertcolor sets the text cursor colour.
    style.configure(
        "TEntry",
        fieldbackground=INPUT_BG, foreground=FG,
        insertcolor=FG, bordercolor=BORDER,
        selectbackground=SELECT, selectforeground=FG,
    )
    # Highlight the border when the entry has focus.
    style.map("TEntry", bordercolor=[("focus", SELECT)])

    # Style for the field and the arrow button.
    style.configure(
        "TCombobox",
        fieldbackground=INPUT_BG, background=BTN_BG,
        foreground=FG, arrowcolor=FG,
        bordercolor=BORDER, selectbackground=SELECT, selectforeground=FG,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", INPUT_BG)],
        foreground=[("readonly", FG)],
        bordercolor=[("focus", SELECT)],
    )
    # The dropdown list is a plain tk.Listbox.
    root.option_add("*TCombobox*Listbox.background",       INPUT_BG)
    root.option_add("*TCombobox*Listbox.foreground",       FG)
    root.option_add("*TCombobox*Listbox.selectBackground", SELECT)
    root.option_add("*TCombobox*Listbox.selectForeground", FG)

    # Scrollbar
    style.configure(
        "TScrollbar",
        background=BTN_BG, troughcolor=BG,
        bordercolor=BORDER, arrowcolor=FG,
    )


def apply_light_mode(root: tk.Tk) -> None:
    """Restyle every ttk widget and the root window to a light colour scheme."""

    # Color palette for light mode.
    BG       = "#f5f5f5"   # window / frame background
    FG       = "#1a1a1a"   # primary text
    INPUT_BG = "#ffffff"   # entry / combobox background
    BTN_BG   = "#e0e0e0"   # button face
    BTN_ACT  = "#cacaca"   # button active / hover
    SELECT   = "#0078d4"   # accent (selection highlight)
    BORDER   = "#aaaaaa"   # widget border / trough

    # Apply background to the root window.
    root.configure(bg=BG)

    style = ttk.Style(root)
    style.theme_use("clam")

    # Base appearance of frame.
    style.configure("TFrame", background=BG)

    # Base appearance of label.
    style.configure("TLabel", background=BG, foreground=FG)

    # Base appearance of button.
    style.configure(
        "TButton",
        background=BTN_BG, foreground=FG,
        bordercolor=BORDER, darkcolor=BTN_BG, lightcolor=BTN_BG,
        relief="flat", padding=4,
    )
    # State-dependent overrides: hover, disabled.
    style.map(
        "TButton",
        background=[("active", BTN_ACT), ("disabled", BG)],
        foreground=[("disabled", BORDER)],
        bordercolor=[("active", SELECT)],
    )

    # Base appearance; insertcolor sets the text cursor colour.
    style.configure(
        "TEntry",
        fieldbackground=INPUT_BG, foreground=FG,
        insertcolor=FG, bordercolor=BORDER,
        selectbackground=SELECT, selectforeground="#ffffff",
    )
    # Highlight the border when the entry has focus.
    style.map("TEntry", bordercolor=[("focus", SELECT)])

    # Style for the visible field and the arrow button.
    style.configure(
        "TCombobox",
        fieldbackground=INPUT_BG, background=BTN_BG,
        foreground=FG, arrowcolor=FG,
        bordercolor=BORDER, selectbackground=SELECT, selectforeground="#ffffff",
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", INPUT_BG)],
        foreground=[("readonly", FG)],
        bordercolor=[("focus", SELECT)],
    )
    # The dropdown list is a plain tk.Listbox — style it via option_add.
    root.option_add("*TCombobox*Listbox.background",       INPUT_BG)
    root.option_add("*TCombobox*Listbox.foreground",       FG)
    root.option_add("*TCombobox*Listbox.selectBackground", SELECT)
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

    # scrollbar
    style.configure(
        "TScrollbar",
        background=BTN_BG, troughcolor=BG,
        bordercolor=BORDER, arrowcolor=FG,
    )


# Path to the small JSON file that remembers the last chosen theme.
PREFS_FILE = Path(__file__).with_name("prefs.json")


def set_title_bar_color(window: tk.Tk, dark: bool) -> None:
    """
    Switch the native Windows title bar between dark and light.
    Requires Windows 10 build 18985+ or Windows 11.
    Silently does nothing on other platforms.
    """
    try:
        import ctypes
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        # GetParent returns the top-level HWND that owns the tkinter canvas.
        hwnd  = ctypes.windll.user32.GetParent(window.winfo_id())
        value = ctypes.c_int(1 if dark else 0)
        # Tell DWM to paint the title bar in dark or light style.
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
    except Exception:
        pass  # non-Windows or unsupported build


def load_theme_preference() -> bool:
    """Return True if dark mode was saved, False (light) otherwise."""
    try:
        import json
        # Read the saved preference from disk; key "dark" holds a bool.
        return json.loads(PREFS_FILE.read_text()).get("dark", False)
    except Exception:
        return False  # default to light if file is missing or unreadable


def save_theme_preference(dark: bool) -> None:
    """Persist the current theme choice to disk."""
    import json
    try:
        # Write a single-key JSON file next to the script.
        PREFS_FILE.write_text(json.dumps({"dark": dark}))
    except Exception:
        pass  # ignore write errors

if HAS_GUI:
    class ImageConverterApp(TkinterDnD.Tk):

        def __init__(self):
            super().__init__()

            # Basic window setup
            self.title("Image Converter")
            self.resizable(False, False)
            self.columnconfigure(0, weight=1)

            # StringVars act as live data bindings between widgets and app state.
            self.file_var   = tk.StringVar()
            self.folder_var = tk.StringVar()
            self.format_var = tk.StringVar(value="jpg")
            self.status_var = tk.StringVar(value="Choose an image file to begin.")

            # Apply the saved theme before any widgets are created so they all
            # inherit the correct colors from the start.
            self._dark = load_theme_preference()
            if self._dark:
                apply_dark_mode(self)
            else:
                apply_light_mode(self)

            # update_idletasks forces Tk to create the native window handle
            # so set_title_bar_color can find it immediately.
            self.update_idletasks()
            set_title_bar_color(self, self._dark)

            # Main container with padding all child widgets live inside this frame.
            frame = ttk.Frame(self, padding=22)
            frame.grid(sticky="nsew")
            frame.columnconfigure(0, weight=1)

            # App title at the top of the form
            ttk.Label(frame, text="Image Converter", font=("Segoe UI", 16, "bold")).grid(
                row=0, column=0, columnspan=2, sticky="w", pady=(0, 14)
            )

            # File and folder picker rows (label + entry + Browse button each)
            self._path_row(frame, 1, "Image file", self.file_var,   self.choose_file)
            self._path_row(frame, 3, "Save to",    self.folder_var, self.choose_folder)

            # Output format selector
            ttk.Label(frame, text="Convert to").grid(row=4, column=0, sticky="w", pady=(12, 0))
            ttk.Combobox(
                frame, textvariable=self.format_var, values=FORMATS,
                state="readonly", width=14,
            ).grid(row=4, column=1, sticky="w", pady=(12, 0))
            # Output format information button
            extension_info_button = ttk.Button(frame, text="What File Type Do I Use?", command=self._file_info)
            extension_info_button.grid(row=4, column=1, columnspan=2, sticky="e", padx=(0,85), pady=(12, 0))

            # Main action button
            self.convert_button = ttk.Button(
                frame, text="Convert image", command=self.start_conversion
            )
            self.convert_button.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(18, 10))

            # Status bar
            ttk.Label(frame, textvariable=self.status_var, wraplength=430).grid(
                row=6, column=0, columnspan=2, sticky="w"
            )

            # Theme toggle button
            self._icon_moon = tk.PhotoImage(file=resource_path("icons/moon.png"))
            self._icon_sun  = tk.PhotoImage(file=resource_path("icons/sun.png"))
            
            # Pick the correct starting icon and colors based on the loaded theme
            starting_icon = self._icon_sun if self._dark else self._icon_moon
            starting_bg   = "#1e1e1e" if self._dark else "#f5f5f5"
            starting_act  = "#505050" if self._dark else "#cacaca"

            self._toggle_btn = tk.Button(
                frame, image=starting_icon, command=self._square_action,
                bg=starting_bg, activebackground=starting_act,
                relief="flat", bd=0,
            )
            self._toggle_btn.grid(row=7, column=1, sticky="e", pady=(8, 2))

        def _square_action(self):
            """Toggle between light and dark mode, update the title bar, and save the preference."""
            if self._dark:
                # Currently dark, switch to light
                apply_light_mode(self)
                self._toggle_btn.configure(bg="#f5f5f5", activebackground="#cacaca", image=self._icon_moon)
            else:
                # Currently light, switch to dark
                apply_dark_mode(self)
                self._toggle_btn.configure(bg="#1e1e1e", activebackground="#505050", image=self._icon_sun)

            self._dark = not self._dark
            set_title_bar_color(self, self._dark)   # sync the native title bar
            save_theme_preference(self._dark)       # persist choice for next launch

        def _file_info(self):
            """Opens info message letting user know which type of file extension to use."""
            messagebox.showinfo(
                "What Type of File Should I Use?",
                "Use png for files with a transparent background.\n\n"
                "Use jpg for all other files and/or if storage space is limited."
            )

        def _path_row(self, parent, row, label, variable, command):
            """Build a labelled row containing a text entry and a Browse button."""
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=5)
            # Inner frame keeps the entry and button together in column 1.
            row_frame = ttk.Frame(parent)
            row_frame.grid(row=row, column=1, sticky="ew", pady=5)
            entry = ttk.Entry(row_frame, textvariable=variable, width=42)
            entry.grid(row=0, column=0, sticky="ew")
            ttk.Button(row_frame, text="Browse…", command=command).grid(row=0, column=1, padx=(7, 0))
            if label == "Image file":
                # Register the entry as a drag-and-drop target for the file field only.
                entry.drop_target_register(DND_FILES)
                entry.dnd_bind("<<Drop>>", self.drop_file)

        def drop_file(self, event):
            """Handle a file being dragged and dropped onto the image file entry."""
            files = self.tk.splitlist(event.data)
            if not files:
                return
            path = Path(files[0])
            if not path.is_file():
                # Reject folders dropped by mistake
                self.status_var.set("Drop an image file, not a folder.")
                return
            self.set_image_file(path)

        def choose_file(self):
            """Open the OS file picker and load the chosen image path."""
            path = filedialog.askopenfilename(title="Choose an image file", filetypes=IMAGE_TYPES)
            if path:
                self.set_image_file(Path(path))

        def set_image_file(self, path):
            """Store the selected image path and pre-fill the output folder if empty."""
            self.file_var.set(str(path))
            if not self.folder_var.get():
                # Default the save location to the same folder as the source file
                self.folder_var.set(str(path.parent))
            self.status_var.set(f"Ready to convert: {path.name}")

        def choose_folder(self):
            """Open the OS folder picker and store the chosen output directory."""
            path = filedialog.askdirectory(title="Choose output folder")
            if path:
                self.folder_var.set(path)

        def start_conversion(self):
            """Validate inputs then kick off the conversion on a background thread."""
            source = self.file_var.get().strip()
            if not source:
                messagebox.showwarning("No image file", "Choose an image file first.")
                return
            if not Path(source).is_file():
                messagebox.showerror("File not found", f"The selected file could not be found:\n{source}")
                return

            # Disable the button to prevent clicks during conversion
            self.convert_button.configure(state="disabled")
            self.status_var.set("Converting image…")
            target_format = self.format_var.get()
            output_dir    = self.folder_var.get().strip() or None

            # Run the conversion on a daemon so the GUI stays responsive
            threading.Thread(
                target=self._convert, args=(source, target_format, output_dir), daemon=True
            ).start()

        def _convert(self, source, target_format, output_dir):
            """Run the conversion helper; post the result back to the GUI thread."""
            try:
                output = convert.image_file(source, target_format, output_dir)
            except Exception as error:
                # Use after() tkinter widgets must only be touched from the main thread.
                self.after(0, self._finished, None, str(error))
            else:
                self.after(0, self._finished, output, None)

        def _finished(self, output, error):
            """Show the conversion result, re-enable the button, and reset the form."""
            self.convert_button.configure(state="normal")
            if error:
                self.status_var.set("Conversion failed.")
                messagebox.showerror("Conversion failed", error)
            else:
                self.status_var.set(f"Done: {output.name}")
                messagebox.showinfo("Conversion complete", f"Saved the converted file to:\n{output}")

            # Clear all fields after conversion is done
            self.file_var.set("")
            self.folder_var.set("")
            self.format_var.set(FORMATS[0])
            self.status_var.set("Choose an image file to begin.")
else:

    def cli():
        """Command-line interface"""
        parser = argparse.ArgumentParser(description="Convert an image to JPG or PNG.")
        parser.add_argument("--file",       help="Path to the image file to convert.")
        parser.add_argument("--new-format", "--new_format", dest="new_format", choices=FORMATS)
        parser.add_argument("--output-dir", help="Folder for the converted file.")
        parser.add_argument("--list", choices=("files", "formats"),
                            help="List supported formats or images in this folder.")
        args = parser.parse_args()

        if args.list == "formats":
            # Print all supported output formats, one per line
            print("\n".join(FORMATS))
        elif args.list == "files":
            # Print image files in the current directory that match a supported format
            for item in Path.cwd().iterdir():
                if item.is_file() and item.suffix.lower().lstrip(".") in FORMATS:
                    print(item.name)
        elif args.file and args.new_format:
            # Run the conversion and print the path of the output file
            print(f"Created: {convert.image_file(args.file, args.new_format, args.output_dir)}")
        else:
            parser.error("use --file with --new-format, or run without options to open the GUI")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        if not HAS_DND:
            print(
                "GUI unavailable: tkinterdnd2 is not installed.\n"
                "Use the command-line interface instead:\n\n"
                "  python main.py --file image.heic --new-format jpg\n"
                "  python main.py --list formats\n"
                "  python main.py --help",
                file=sys.stderr,
            )
            raise SystemExit(1)
        ImageConverterApp().mainloop()
    else:
        try:
            cli()
        except Exception as error:
            print(f"Error: {error}", file=sys.stderr)
            raise SystemExit(1)