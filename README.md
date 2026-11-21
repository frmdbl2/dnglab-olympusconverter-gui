# Olympus ORF Converter

A Windows desktop tool for batch-converting **Olympus camera RAW (`.ORF`) files to Adobe DNG** with **lossless** compression, powered by [dnglab](https://github.com/dnglab/dnglab).

Built with Python + Tkinter (wrapped with `tkinterdnd2` for drag & drop) and shipped as a standalone `.exe` via PyInstaller.

![Olympus ORF Converter v0.1](https://img.shields.io/badge/version-0.1-blue) ![Platform](https://img.shields.io/badge/platform-Windows-0078D6) ![Python](https://img.shields.io/badge/python-3.x-3776AB)

## Features

- **Lossless RAW → DNG conversion** using `dnglab convert -c lossless`
- **Drag & drop** ORF files or folders directly onto the window
- **Batch processing** with a progress bar, live log, and success/failed/skipped counts
- **Recursive folder scanning** (optional)
- **Skip existing DNG files** to avoid re-converting
- **Custom output folder** or automatic `OUT` folder beside each source ORF
- **Dark / light theme** toggle (persisted)
- **DPI-aware, responsive UI** that stays usable at 125% / 150% Windows scaling
- **Settings persistence** (`~/.olympus_converter_settings.json`)
- **Stop after current file** without killing the whole batch
- Bundled as a single **standalone Windows executable** (`OlympusConverter.exe`)

## Requirements

- Windows (uses `CREATE_NO_WINDOW` and DPI work-area detection)
- `dnglab.exe` (v0.8.0+) — download from the [dnglab releases](https://github.com/dnglab/dnglab/releases) and point the app at it
- Python 3.x + dependencies (only if running from source):
  - `tkinter` (bundled with CPython on Windows)
  - `tkinterdnd2`

## Running from source

```bash
pip install tkinterdnd2
python OlympusConverter.py
```

On first launch, click **Browse…** next to *DNGLab executable* and select your `dnglab.exe`.

## Building the standalone executable

The project ships a PyInstaller spec (`OlympusConverter.spec`):

```bash
pyinstaller OlympusConverter.spec
```

The resulting `OlympusConverter.exe` lands in `dist/`.

## Usage

1. Select (or drag & drop) `.ORF` files / folders.
2. Choose the `dnglab.exe` path and an optional output folder.
3. Toggle *Include subfolders* / *Skip existing DNG files* as needed.
4. Click **Start conversion**.
5. Watch progress in the log; use **Stop after current file** to abort mid-batch.

## Notes

- Conversion is **lossless** — no quality is lost; only the container format changes.
- Output defaults to an `OUT` folder created next to each source ORF when no output folder is set.
- Settings (exe path, output path, recursive/skip/dark-mode flags) are saved automatically on close.

## License

This project is licensed under the **GNU General Public License v3.0** (GPL-3.0).
See the [LICENSE](LICENSE) file for the full text.

Note: this tool wraps [dnglab](https://github.com/dnglab/dnglab), which is distributed under its own license — please review dnglab's terms separately.
