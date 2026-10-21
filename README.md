# Cull

**A photo culling assistant that finds blurry, poorly exposed, and duplicate shots so photographers can focus on choosing the best ones.**

![Status](https://img.shields.io/badge/status-in%20development-yellow)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

<!-- Demo GIF goes here once the review UI is available -->

---

## Overview

A typical photo shoot produces hundreds or thousands of frames, most of which will never be used. Sorting through them by hand is slow and repetitive. Cull automates the technical side of that process, it analyzes every photo in a folder, groups similar shots together, and recommends the strongest frame in each group.

All final decisions remain with the photographer. Cull will never deletes or modify original files.

## Features

| Feature | Description |
| --- | --- |
| Sharpness detection | Flags out-of-focus and motion-blurred frames, measured on the subject rather than the whole image |
| Exposure analysis | Detects blown highlights and crushed shadows using histogram clipping |
| Burst grouping | Groups related shots by capture time and visual similarity |
| Duplicate detection | Identifies near-identical images with perceptual hashing |
| Blink detection | Flags frames where a subject's eyes are closed |
| Explainable scoring | Every recommendation includes a plain-language reason |
| Keyboard-driven review | Fast pick/reject workflow in a local web interface |
| XMP export | Writes ratings and flags readable by Lightroom, darktable, and Capture One |
| RAW support | Reads common RAW formats (CR3, NEF, ARW, and others) via embedded previews |
| Non-destructive | Original files are never altered or deleted |

## How It Works

Cull processes a folder in five stages:

1. **Ingest** – Discovers image files, reads EXIF metadata, and extracts embedded JPEG previews from RAW files for fast analysis.
2. **Analyze** – Scores each image for sharpness (variance of the Laplacian), exposure (histogram clipping), and, where faces are present, eye state (eye aspect ratio).
3. **Group** – Clusters images captured within a short time window that share similar perceptual hashes.
4. **Rank** – Compares images within each group and selects a suggested pick, using relative rather than absolute thresholds.
5. **Review and export** – Presents results in a review interface and writes decisions to XMP sidecar files.

Analysis results are cached in a local SQLite database, so reopening a previously scanned folder is near-instant.

## Installation

> Cull is under active development. Installation instructions will be finalized with the first release.

**Planned:**

```bash
pipx install cull
```

**With uv (recommended):**

```bash
git clone https://github.com/candycain5432/Cull.git
cd cull
uv tool install .

```

**With pip:**

```bash
git clone https://github.com/candycain5432/Cull.git
cd Cull
python -m venv .venv
source .venv/bin/activate
pip install .
```

### Requirements

- Python 3.12 or newer
- Linux, macOS, or Windows

## Usage

Scan a folder and print a report:

```bash
cull scan ./shoot
```

Open the review interface:

```bash
cull review ./shoot
```

Export decisions as XMP sidecar files:

```bash
cull export ./shoot --format xmp
```

### Review Controls

| Key | Action |
| --- | --- |
| `P` | Mark as pick |
| `X` | Mark as reject |
| `←` / `→` | Previous / next image |
| `↑` / `↓` | Previous / next group |
| `C` | Toggle side-by-side compare |

## Project Structure

```
cull/
├── cli/            Command-line entry point
├── ingest/         File discovery, EXIF reading, preview extraction
├── analysis/
│   ├── sharpness   Laplacian-based sharpness scoring
│   ├── exposure    Histogram clipping detection
│   ├── faces       Face and eye detection
│   └── similarity  Perceptual hashing
├── grouping/       Burst and duplicate clustering
├── scoring/        Metric combination, ranking, and explanations
├── storage/        SQLite cache
├── export/         XMP writer and file organization
└── ui/             Review interface
tests/
└── fixtures/       Labeled sample images
```

## Tech Stack

| Area | Tools |
| --- | --- |
| Image analysis | OpenCV, NumPy |
| RAW and metadata | rawpy, exifread |
| Similarity | imagehash |
| Face and eye detection | MediaPipe |
| Storage | SQLite |
| Review interface | FastAPI, HTML/CSS/JavaScript |
| Testing and CI | pytest, GitHub Actions |

## Roadmap

### v0.1 – Core analysis
- [ ] Folder scanning and EXIF reading
- [ ] RAW preview extraction
- [ ] Sharpness and exposure scoring
- [ ] SQLite result cache
- [ ] Burst and duplicate grouping
- [ ] Command-line report

### v0.2 – Review interface
- [ ] Grid view of grouped images
- [ ] Keyboard pick/reject controls
- [ ] Side-by-side compare view

### v0.3 – Smarter analysis
- [ ] Face detection
- [ ] Subject-aware sharpness
- [ ] Blink detection
- [ ] Relative exposure thresholds

### v0.4 – Workflow integration
- [ ] XMP sidecar export
- [ ] Optional reject folder

### v1.0 – Release
- [ ] Multiprocessing
- [ ] Accuracy benchmark against a labeled dataset
- [ ] Full test coverage and CI
- [ ] PyPI release

## Accuracy

Benchmark results will be published here once evaluation against a hand-labeled dataset is complete.

## Contributing

Contributions, bug reports, and feature requests are welcome. Please open an issue to discuss significant changes before submitting a pull request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Open a pull request

## License

Distributed under the MIT License. See `LICENSE` for details.
