# Dataset Empty Label Generator

A local Streamlit application that scans an uploaded image directory and creates matching, zero-byte label files in an in-memory ZIP. It is designed for preparing machine-learning and computer-vision datasets without changing source images.

## Features

- Whole-directory upload with drag-and-drop support
- Optional recursive scanning and folder-structure preservation
- Case-insensitive support for JPG, JPEG, PNG, WEBP, BMP, TIF, TIFF, and GIF
- Built-in and validated custom label extensions
- Preview, search, status filtering, metrics, and issue reporting
- Case-insensitive filename-collision protection for Windows
- In-memory ZIP generation; every label entry is exactly 0 bytes
- Optional UTF-8 CSV generation report
- No image decoding and no source-folder writes

## Requirements

- Python 3.11 or newer
- A current desktop browser with directory-upload support

## Installation

Clone or copy this project, then open a terminal in its root directory.

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` in that terminal and activate again.

### Linux or macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run the application

```bash
streamlit run app.py
```

Open the local URL printed by Streamlit, normally <http://localhost:8501>.

## Usage

1. Select or drop an image folder into the uploader.
2. Choose a label extension and folder options.
3. Review the summary, mapping preview, and Issues tab.
4. Choose how collisions should be handled. `Skip duplicates` is the safe default.
5. Select **Generate empty labels**, then **Download labels.zip**.

The downloaded archive always stores outputs below `labels/`:

```text
labels.zip
└── labels/
    ├── eagle.txt
    ├── owl.txt
    └── pigeon.final.v2.txt
```

With structure preservation enabled:

```text
dataset/
├── birds/eagle.jpg
└── planes/plane01.png

labels/
├── birds/eagle.txt
└── planes/plane01.txt
```

Only the final image suffix is replaced, so `my.image.001.jpg` becomes `my.image.001.txt`. Spaces, Unicode, and uppercase image extensions are supported.

## Supported image extensions

`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tif`, `.tiff`, `.gif` (case-insensitive)

## Supported label extensions

`.txt`, `.csv`, `.json`, `.jsonl`, `.xml`, `.yaml`, `.yml`, `.label`, plus a validated custom extension such as `.ann` or `bbox` (normalized to `.bbox`). The extension changes only the name; generated label contents always remain empty.

## Collision handling

`bird.jpg` and `bird.png` both map to `bird.txt`. The app identifies this before generation and compares paths case-insensitively. Available policies are:

- **Skip duplicates:** create no output for the entire colliding group (default)
- **Keep first file:** create the shared empty label once and report the others as skipped
- **Preserve directory structure:** retain relative folders, resolving collisions that occur only across folders; unresolved same-folder collisions are skipped
- **Cancel generation:** refuse to build the ZIP while collisions remain

No policy can silently overwrite a ZIP entry.

## Optional generation report

Enable **Include generation report** to add `labels/label_generation_report.csv`. This report contains mapping metadata; it does not change the zero-byte label files.

## Testing

```bash
python -m pytest -q
```

The test suite covers normal, multi-period, uppercase, spaced, and Unicode names; custom extensions; collisions; structure preservation; the supplied verification dataset; and exact zero-byte ZIP contents.

## Project structure

```text
.
├── app.py                    # Streamlit UI
├── label_generator.py        # Mapping, statistics, and ZIP generation
├── validators.py             # Extension, filename, path, and collision checks
├── requirements.txt
├── README.md
├── .gitignore
└── tests/
    ├── test_label_generator.py
    └── test_validators.py
```

## Troubleshooting

- **No files appear:** Choose the folder itself, not individual images. Check that the browser supports directory selection.
- **Nested files are missing:** Enable **Include subfolders**.
- **No label is created for a file:** Confirm its extension is in the supported list and inspect the Issues tab.
- **Generation is blocked:** Select a collision policy other than **Cancel generation**, or preserve folders when duplicate stems are in different directories.
- **Large upload fails:** Streamlit's default upload limit is 200 MB per individual file. This app does not read image bytes, but the browser and Streamlit must still transfer the selected directory metadata/files.
- **`streamlit` is not recognized:** Activate the virtual environment, or run `python -m streamlit run app.py`.

## Safety

Uploaded data is read-only. The application uses uploaded path metadata to build an in-memory ZIP and never deletes, renames, moves, modifies, overwrites, or writes beside source images.
