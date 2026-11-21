# Olympus ORF Converter
# Copyright (C) 2026
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
from pathlib import Path
import subprocess
import threading
import queue
import shutil
import json

APP_NAME = "Olympus ORF Converter"
SETTINGS_FILE = Path.home() / ".olympus_converter_settings.json"


class Converter:

    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME + " v0.1")
        self.setup_window()

        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.running = False
        self.files = []

        self.settings = self.load_settings()

        self.exe = tk.StringVar(
            value=self.settings.get("exe", "")
        )
        self.output = tk.StringVar(
            value=self.settings.get("output", "")
        )
        self.recursive = tk.BooleanVar(
            value=self.settings.get("recursive", False)
        )
        self.skip = tk.BooleanVar(
            value=self.settings.get("skip", True)
        )
        self.dark_mode = tk.BooleanVar(
            value=self.settings.get("dark_mode", True)
        )

        self.style = ttk.Style()
        self.style.theme_use("clam")

        self._relayouting = False

        self.configure_theme()
        self.build_ui()

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.on_drop)

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Configure>", self.relayout, add="+")
        self.root.after(100, self.relayout)
        self.root.after(100, self.process_events)

    # WINDOW SIZING (fits 1366x768 and DPI-scaled screens)

    def work_area(self):
        """Work area (screen minus taskbar) in Tk coordinates.

        Uses the same coordinate space as Tk, so it stays correct
        at 100%, 125% and 150% Windows display scaling.
        """
        try:
            import ctypes
            from ctypes import wintypes

            rect = wintypes.RECT()
            ok = ctypes.windll.user32.SystemParametersInfoW(
                0x0030, 0, ctypes.byref(rect), 0  # SPI_GETWORKAREA
            )
            if ok:
                return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            pass

        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight()
        return 0, 0, width, max(height - 48, height * 3 // 4)

    def setup_window(self):
        """Default 850x700, centred, never larger than the work area."""
        left, top, right, bottom = self.work_area()
        avail_w = right - left
        avail_h = bottom - top

        width = min(850, avail_w - 16)
        height = min(700, avail_h - 16)
        width = max(width, min(640, avail_w - 16))
        height = max(height, min(430, avail_h - 16))

        x = left + max(0, (avail_w - width) // 2)
        y = top + max(0, (avail_h - height) // 2)

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(min(640, width), min(430, height))

    # SETTINGS

    def load_settings(self):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def save_settings(self):
        data = {
            "exe": self.exe.get(),
            "output": self.output.get(),
            "recursive": self.recursive.get(),
            "skip": self.skip.get(),
            "dark_mode": self.dark_mode.get()
        }

        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass

    def close(self):
        if self.running:
            if not messagebox.askyesno(
                "Conversion running",
                "A conversion is running. Close anyway?"
            ):
                return

        self.save_settings()
        self.root.destroy()

    # THEME

    def configure_theme(self):
        if self.dark_mode.get():
            self.colors = {
                "bg": "#17191F",
                "panel": "#22252E",
                "input": "#2D303A",
                "fg": "#F0F1F5",
                "muted": "#A0A5B3",
                "accent": "#648CFF",
                "accent_hover": "#7CA0FF",
                "border": "#383C48",
                "log": "#111319"
            }
        else:
            self.colors = {
                "bg": "#F1F3F7",
                "panel": "#FFFFFF",
                "input": "#F7F8FA",
                "fg": "#20232B",
                "muted": "#707784",
                "accent": "#3869D4",
                "accent_hover": "#2858BD",
                "border": "#D8DCE5",
                "log": "#FFFFFF"
            }

        c = self.colors
        self.root.configure(bg=c["bg"])

        self.style.configure(
            ".", background=c["bg"], foreground=c["fg"],
            font=("Segoe UI", 10)
        )
        self.style.configure("TFrame", background=c["bg"])
        self.style.configure(
            "TLabel", background=c["bg"], foreground=c["fg"]
        )
        self.style.configure(
            "Muted.TLabel",
            background=c["bg"], foreground=c["muted"]
        )
        self.style.configure(
            "Title.TLabel",
            background=c["bg"], foreground=c["fg"],
            font=("Segoe UI", 16, "bold")
        )
        self.style.configure(
            "Section.TLabel",
            background=c["bg"], foreground=c["fg"],
            font=("Segoe UI", 11, "bold")
        )
        self.style.configure(
            "TButton",
            background=c["panel"], foreground=c["fg"],
            bordercolor=c["border"], padding=(10, 5)
        )
        self.style.map(
            "TButton",
            background=[("active", c["input"])]
        )
        self.style.configure(
            "Accent.TButton",
            background=c["accent"], foreground="#FFFFFF",
            bordercolor=c["accent"], padding=(14, 7),
            font=("Segoe UI", 10, "bold")
        )
        self.style.map(
            "Accent.TButton",
            background=[("active", c["accent_hover"])]
        )
        self.style.configure(
            "TEntry",
            fieldbackground=c["input"],
            foreground=c["fg"],
            insertcolor=c["fg"],
            bordercolor=c["border"],
            padding=5
        )
        self.style.configure(
            "TCheckbutton",
            background=c["bg"], foreground=c["fg"]
        )
        self.style.map(
            "TCheckbutton",
            background=[("active", c["bg"])],
            foreground=[("active", c["fg"])]
        )
        self.style.configure(
            "TProgressbar",
            background=c["accent"],
            troughcolor=c["input"],
            bordercolor=c["border"],
            thickness=12
        )

    def toggle_theme(self):
        self.dark_mode.set(not self.dark_mode.get())
        self.configure_theme()
        self.update_log_theme()

        self.theme_button.config(
            text="☀ Light mode" if self.dark_mode.get()
            else "☾ Dark mode"
        )
        self.save_settings()

    # INTERFACE

    def build_ui(self):
        c = self.colors

        main = ttk.Frame(self.root, padding=(10, 6, 10, 6))
        main.pack(fill="both", expand=True)

        # Scrollable content area: keeps every control reachable on
        # short or DPI-scaled screens (125% / 150% scaling).
        self.scroll_wrap = ttk.Frame(main)
        self.scroll_wrap.pack(fill="x")

        self.canvas = tk.Canvas(
            self.scroll_wrap,
            highlightthickness=0,
            bd=0,
            bg=c["bg"]
        )
        self.vsb = ttk.Scrollbar(
            self.scroll_wrap,
            orient="vertical",
            command=self.canvas.yview
        )
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")
        self.vsb_shown = True

        content = ttk.Frame(self.canvas)
        self.content = content
        self.content_window = self.canvas.create_window(
            (0, 0), window=content, anchor="nw"
        )

        content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        # Header
        header = ttk.Frame(content)
        header.pack(fill="x", pady=(0, 6))

        heading = ttk.Frame(header)
        heading.pack(side="left")

        ttk.Label(
            heading,
            text="Olympus ORF Converter",
            style="Title.TLabel"
        ).pack(anchor="w")

        ttk.Label(
            heading,
            text="Lossless RAW to DNG conversion  •  v0.1",
            style="Muted.TLabel"
        ).pack(anchor="w", pady=(1, 0))

        self.theme_button = ttk.Button(
            header,
            text="☀ Light mode" if self.dark_mode.get()
            else "☾ Dark mode",
            command=self.toggle_theme
        )
        self.theme_button.pack(side="right")

        # DNGLab executable
        self.path_row(
            content, "DNGLab executable",
            self.exe, self.choose_exe
        )

        # Compact drag & drop target (~76 px high)
        self.drop_area = tk.Frame(
            content,
            height=76,
            bg=c["input"],
            highlightthickness=1,
            highlightbackground=c["border"],
            cursor="hand2"
        )
        self.drop_area.pack(fill="x", pady=(2, 5))
        self.drop_area.pack_propagate(False)

        self.drop_label = tk.Label(
            self.drop_area,
            text="↧  Drop ORF files or folders here"
                 "  —  or click to add files",
            font=("Segoe UI", 11),
            bg=c["input"],
            fg=c["fg"],
            cursor="hand2",
            justify="center"
        )
        self.drop_label.pack(fill="both", expand=True)

        for widget in (self.drop_area, self.drop_label):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self.on_drop)
            widget.bind(
                "<Button-1>",
                lambda e: self.choose_files()
            )

        # Add files / Add folder
        buttons = ttk.Frame(content)
        buttons.pack(fill="x", pady=(0, 3))

        ttk.Button(
            buttons, text="+ Add files",
            command=self.choose_files
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            buttons, text="+ Add folder",
            command=self.choose_folder
        ).pack(side="left")

        self.file_label = ttk.Label(
            content, text="No files selected",
            style="Muted.TLabel"
        )
        self.file_label.pack(anchor="w", pady=(0, 5))

        # Output folder
        self.path_row(
            content,
            "Output folder (optional - blank uses OUT beside each ORF)",
            self.output,
            self.choose_output
        )

        # Conversion settings
        ttk.Label(
            content, text="Conversion settings",
            style="Section.TLabel"
        ).pack(anchor="w", pady=(6, 3))

        ttk.Label(
            content, text="Compression: LOSSLESS",
            style="Muted.TLabel"
        ).pack(anchor="w", pady=(0, 3))

        options = ttk.Frame(content)
        options.pack(fill="x", pady=(0, 2))

        ttk.Checkbutton(
            options,
            text="Include subfolders when adding folders",
            variable=self.recursive
        ).pack(side="left")

        ttk.Checkbutton(
            options,
            text="Skip existing DNG files",
            variable=self.skip
        ).pack(side="left", padx=(18, 0))

        # Progress (fixed - never scrolls away)
        self.progress_block = ttk.Frame(main)
        self.progress_block.pack(fill="x", pady=(6, 0))

        ttk.Label(
            self.progress_block, text="Conversion progress",
            style="Section.TLabel"
        ).pack(anchor="w", pady=(0, 3))

        self.progress = ttk.Progressbar(
            self.progress_block, maximum=100, mode="determinate"
        )
        self.progress.pack(fill="x")

        self.status = ttk.Label(
            self.progress_block, text="Ready", style="Muted.TLabel"
        )
        self.status.pack(anchor="w", pady=(3, 0))

        # Log (flexible - absorbs the remaining space)
        self.log_block = ttk.Frame(main)
        self.log_block.pack(fill="both", expand=True, pady=(4, 2))

        ttk.Label(
            self.log_block, text="Conversion log",
            style="Section.TLabel"
        ).pack(anchor="w", pady=(0, 2))

        log_row = ttk.Frame(self.log_block)
        log_row.pack(fill="both", expand=True)

        self.log = tk.Text(
            log_row, height=4, wrap="word",
            font=("Consolas", 9),
            relief="flat", padx=6, pady=6
        )

        scrollbar = ttk.Scrollbar(
            log_row, command=self.log.yview
        )

        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Start / Stop (fixed at the bottom - always visible)
        self.actions_row = ttk.Frame(main)
        self.actions_row.pack(fill="x", pady=(6, 0))

        self.start_button = ttk.Button(
            self.actions_row, text="Start conversion",
            style="Accent.TButton", command=self.start
        )
        self.start_button.pack(side="left")

        self.stop_button = ttk.Button(
            self.actions_row, text="Stop after current file",
            command=self.stop, state="disabled"
        )
        self.stop_button.pack(side="left", padx=10)

        self.update_log_theme()
        self.bind_mousewheel(self.content)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel, add="+")

    def path_row(self, parent, label, variable, command):
        ttk.Label(
            parent, text=label,
            style="Section.TLabel"
        ).pack(anchor="w", pady=(0, 1))

        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(0, 4))

        ttk.Entry(
            row, textvariable=variable
        ).pack(side="left", fill="x", expand=True)

        ttk.Button(
            row, text="Browse...", command=command
        ).pack(side="left", padx=(8, 0))

    # LAYOUT REFLOW

    def on_canvas_configure(self, event):
        self.canvas.itemconfig(self.content_window, width=event.width)

    def on_mousewheel(self, event):
        delta = int(round(event.delta / 120))
        if delta:
            self.canvas.yview_scroll(-delta, "units")

    def bind_mousewheel(self, widget):
        widget.bind("<MouseWheel>", self.on_mousewheel, add="+")
        for child in widget.winfo_children():
            self.bind_mousewheel(child)

    def relayout(self, event=None):
        """Size the scrollable area so Start/Stop stay visible.

        Everything except the log has a fixed height; the log absorbs
        the remaining space. If the window is too short for all of the
        content (small logical desktop under 125%/150% scaling), the
        content area scrolls while the progress bar, log and the
        Start/Stop buttons stay fixed.
        """
        if event is not None and event.widget is not self.root:
            return
        if self._relayouting or not self.root.winfo_ismapped():
            return

        self._relayouting = True
        try:
            self.root.update_idletasks()

            client = self.root.winfo_height()
            content = self.content.winfo_reqheight()

            # Main padding + gaps between the fixed blocks.
            fixed = (
                30
                + self.progress_block.winfo_reqheight()
                + self.log_block.winfo_reqheight()
                + self.actions_row.winfo_reqheight()
            )

            room = client - fixed
            height = content if content <= room else max(room, 140)
            self.canvas.configure(height=height)

            scroll = content > room
            if scroll and not self.vsb_shown:
                self.vsb.pack(side="right", fill="y")
                self.vsb_shown = True
            elif not scroll and self.vsb_shown:
                self.vsb.pack_forget()
                self.vsb_shown = False
                self.canvas.yview_moveto(0)
        finally:
            self._relayouting = False

    def update_log_theme(self):
        c = self.colors
        self.log.configure(
            bg=c["log"], fg=c["fg"],
            insertbackground=c["fg"],
            selectbackground=c["accent"]
        )
        self.canvas.configure(bg=c["bg"])
        self.drop_area.configure(
            bg=c["input"], highlightbackground=c["border"]
        )
        self.drop_label.configure(
            bg=c["input"], fg=c["fg"]
        )
        
  # FILE SELECTION AND DRAG & DROP

    def add_paths(self, paths):
        added = 0

        for path_string in paths:
            path = Path(path_string)

            if not path.exists():
                continue

            if path.is_file():
                candidates = (
                    [path] if path.suffix.lower() == ".orf" else []
                )

            elif path.is_dir():
                if self.recursive.get():
                    candidates = [
                        p for p in path.rglob("*")
                        if p.is_file() and p.suffix.lower() == ".orf"
                    ]
                else:
                    candidates = [
                        p for p in path.iterdir()
                        if p.is_file() and p.suffix.lower() == ".orf"
                    ]
            else:
                candidates = []

            for candidate in candidates:
                if candidate not in self.files:
                    self.files.append(candidate)
                    added += 1

        self.files.sort(key=lambda p: str(p).lower())
        self.update_file_label()

        if added:
            self.write_log(f"Added {added} file(s).")

    def on_drop(self, event):
        try:
            paths = self.root.tk.splitlist(event.data)
            self.add_paths(paths)
        except Exception as error:
            self.write_log(f"Drop error: {error}")

    def choose_files(self):
        paths = filedialog.askopenfilenames(
            title="Select Olympus ORF files",
            filetypes=[
                ("Olympus RAW files", "*.orf"),
                ("All files", "*.*")
            ]
        )

        if paths:
            self.add_paths(paths)

    def choose_folder(self):
        folder = filedialog.askdirectory(
            title="Select folder containing ORF files"
        )

        if folder:
            self.add_paths([folder])

    def choose_exe(self):
        path = filedialog.askopenfilename(
            title="Select DNGLab executable",
            filetypes=[
                ("Executable", "*.exe"),
                ("All files", "*.*")
            ]
        )

        if path:
            self.exe.set(path)
            self.save_settings()

    def choose_output(self):
        folder = filedialog.askdirectory(
            title="Select output folder"
        )

        if folder:
            self.output.set(folder)
            self.save_settings()

    def update_file_label(self):
        self.file_label.config(
            text=f"{len(self.files)} ORF file(s) selected"
        )
        self.relayout()

    # LOGGING

    def write_log(self, text):
        if text:
            self.log.insert("end", str(text) + "\n")
            self.log.see("end")

    # START CONVERSION

    def start(self):
        if self.running:
            return

        exe = Path(self.exe.get())

        if not exe.is_file():
            messagebox.showerror(
                "DNGLab missing",
                "Please select your dnglab.exe."
            )
            return

        if not self.files:
            messagebox.showerror(
                "No files",
                "Please add ORF files or folders."
            )
            return



        destination = self.output.get()

        if destination:
            try:
                Path(destination).mkdir(parents=True, exist_ok=True)
            except OSError as error:
                messagebox.showerror("Output error", str(error))
                return

        self.save_settings()

        self.running = True
        self.stop_event.clear()

        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress["value"] = 0
        self.log.delete("1.0", "end")

        files = list(self.files)
        output = str(destination)
        executable = str(exe)
        skip = self.skip.get()

        self.write_log("Starting lossless conversion...")
        self.write_log(f"Files: {len(files)}")
        self.write_log(f"Output: {output}")
        self.write_log("--------------------------------")

        threading.Thread(
            target=self.convert,
            args=(files, executable, output, skip),
            daemon=True
        ).start()

    # CONVERSION ENGINE

    def convert(self, files, exe, output, skip):
        destination = Path(output) if output else None


        success = 0
        failed = 0
        skipped = 0
        total = len(files)

        for index, source in enumerate(files, 1):
            if destination is None:
                current_output = source.parent / "OUT"
            else:
                current_output = destination
                current_output.mkdir(parents=True, exist_ok=True)
      
            
            if self.stop_event.is_set():
                break

            # DNGLab creates output using the original filename.
            target = current_output / (source.stem + ".dng")


            if skip and target.exists():
                skipped += 1
                self.events.put((
                    "log",
                    f"SKIPPED: {source.name}"
                ))

            else:
                self.events.put((
                    "status",
                    f"Converting {index}/{total}: {source.name}"
                ))

                self.events.put((
                    "log",
                    f"Converting: {source}"
                ))

                command = [
                    exe,
                    "convert",
                    "-c",
                    "lossless",
                    str(source),
                    str(current_output)
                ]

                try:
                    result = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        errors="replace",
                        creationflags=getattr(
                            subprocess,
                            "CREATE_NO_WINDOW",
                            0
                        )
                    )

                    if result.stdout.strip():
                        self.events.put((
                            "log",
                            result.stdout.strip()
                        ))

                    if result.stderr.strip():
                        self.events.put((
                            "log",
                            result.stderr.strip()
                        ))

                    if result.returncode == 0 and target.exists():
                        success += 1
                        self.events.put((
                            "log",
                            f"SUCCESS: {target.name}"
                        ))
                    else:
                        failed += 1
                        self.events.put((
                            "log",
                            f"FAILED: {source.name}"
                        ))
                        self.events.put((
                            "log",
                            f"Exit code: {result.returncode}"
                        ))

                        if result.returncode == 0:
                            self.events.put((
                                "log",
                                f"Expected output missing: {target}"
                            ))

                except Exception as error:
                    failed += 1
                    self.events.put((
                        "log",
                        f"ERROR: {error}"
                    ))

            self.events.put((
                "progress",
                index / total * 100
            ))

            self.events.put((
                "counts",
                (success, failed, skipped, total)
            ))

        stopped = self.stop_event.is_set()

        self.events.put((
            "done",
            (success, failed, skipped, stopped)
        ))

    # STOP CONVERSION

    def stop(self):
        self.stop_event.set()

        self.stop_button.config(state="disabled")

        self.status.config(
            text="Stopping after current file..."
        )

        self.write_log(
            "Stop requested. Waiting for current file..."
        )

    # EVENT HANDLING

    def process_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()

                if kind == "log":
                    self.write_log(value)

                elif kind == "status":
                    self.status.config(text=value)

                elif kind == "progress":
                    self.progress["value"] = value

                elif kind == "counts":
                    success, failed, skipped, total = value

                    self.status.config(
                        text=(
                            f"Converted: {success} | "
                            f"Failed: {failed} | "
                            f"Skipped: {skipped} | "
                            f"Total: {total}"
                        )
                    )

                elif kind == "done":
                    success, failed, skipped, stopped = value

                    self.running = False

                    self.start_button.config(state="normal")
                    self.stop_button.config(state="disabled")

                    self.status.config(
                        text=(
                            f"Finished: {success} converted, "
                            f"{failed} failed, "
                            f"{skipped} skipped"
                        )
                    )

                    self.write_log("--------------------------------")
                    self.write_log("CONVERSION FINISHED")
                    self.write_log(f"Converted: {success}")
                    self.write_log(f"Failed: {failed}")
                    self.write_log(f"Skipped: {skipped}")

                    if stopped:
                        self.write_log("Stopped by user.")
                    elif failed == 0:
                        self.write_log(
                            "All files converted successfully."
                        )

        except queue.Empty:
            pass

        self.root.after(100, self.process_events)


# APPLICATION START

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = Converter(root)
    root.mainloop()
