# Cull

**A photo culling assistant that finds blurry, poorly exposed, and duplicate shots so photographers can focus on choosing the best ones.**

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

<!-- Demo GIF goes here once the review UI is available -->

---

## Overview

A typical photo shoot produces hundreds or thousands of frames, most of which will never be used. Sorting through them by hand is slow and repetitive. Cull automates the technical side of that process: it scores every photo in a folder, groups similar shots together, and suggests the strongest frame in each group, with a plain-language reason for every decision.

All final decisions remain with the photographer. Cull never deletes or edits a photo.

## Features

| Feature | Description |
| --- | --- |
| Sharpness ranking | Ranks photos from sharpest to blurriest using the variance of the Laplacian |
| Exposure analysis | Detects blown highlights and crushed shadows using histogram clipping |
| Burst grouping | Groups related shots by capture time and visual similarity |
| Duplicate detection | Finds copies with perceptual hashing, even if they were resized, rotated, or lost their EXIF data |
| Suggested picks | Picks the best frame in each group and explains every decision |
| Group folders | Lays the groups out as folders without moving your originals |
| RAW support | Reads CR2, CR3, NEF, ARW, DNG, ORF, RW2, and RAF files through their embedded previews |
| Instant repeat runs | Results are cached in SQLite, so a second run doesn't reopen any photos |

## Installation

**With uv (recommended):**

```bash
uv tool install git+https://github.com/candycain5432/Cull.git
```

**With pipx:**

```bash
pipx install git+https://github.com/candycain5432/Cull.git
```

**From a clone:**

```bash
git clone https://github.com/candycain5432/Cull.git
cd Cull
python -m venv .venv
source .venv/bin/activate
pip install .
```

> Don't run `pip install cull` or `pipx install cull`. A different project already uses that name on PyPI.

### Requirements

- Python 3.12 or newer
- Developed and tested on Linux. macOS and Windows should work but haven't been tested yet.

## Usage

| Command | What it does |
| --- | --- |
| `cull group ./shoot` | Groups similar shots, suggests the best of each, and writes the group folders |
| `cull score ./shoot` | Shows every score for every photo |
| `cull sharpness ./shoot` | Ranks photos from sharpest to blurriest |
| `cull exposure ./shoot` | Ranks photos from best to worst exposed |
| `cull scan ./shoot` | Prints the EXIF data of every photo |
| `cull sort ./shoot` | Moves photos into folders by file type |

`cull group` is the one most people want:

```
$ cull group ./shoot

 === Burst, 3 photos ===
PICK  DSC1070.jpg  Sharpest, next best is DSC1069.jpg at 92% less sharp, DSC1071.jpg is sharper but 80.5% clipped against 5.8%
      DSC1069.jpg  92% less sharp than the pick
      DSC1071.jpg  80.5% clipped, the pick is 5.8%
```

It also creates a `shoot_groups` folder next to `shoot`, with one folder per group and the suggested frame marked `PICK_`:

```
shoot_groups/
├── 001_burst/
│   ├── PICK_DSC1070.jpg
│   ├── DSC1069.jpg
│   └── DSC1071.jpg
├── 002_duplicates/
└── singles/
```

The files in there are hard links, so they take no extra disk space and your originals stay where they are. Two things to know about that:

- Deleting a photo from `shoot_groups` doesn't delete the original.
- A program that saves over a file in `shoot_groups` also changes the original, because they are the same file. Edit a copy if you're unsure.

If a drive can't do hard links, Cull makes normal copies instead. Cull never overwrites an existing `shoot_groups` folder, so delete it to rebuild it.

## How It Works

1. **Read** – Finds every photo in the folder, including subfolders. RAW files use their embedded JPEG preview.
2. **Score** – Measures sharpness, clipped highlights and shadows, and brightness, and reads the capture time and camera from the EXIF data.
3. **Group** – Links photos using three rules:
   - **Burst:** same camera, 1 second apart or less
   - **Similar shots:** same camera, within 30 seconds, and they look alike
   - **Duplicates:** near-identical, with the same capture time or a missing date
4. **Pick** – Within each group, drops undersized copies, then frames with 5 or more points of extra clipping, and picks the sharpest of what's left.

Results are saved to `~/.cache/cull/cache.db`. A photo is only analyzed again if its size or modified time changes. It's safe to delete this file at any time.

## Limitations

- **Sharpness is measured on the whole frame.** A blurred subject on a sharp background can score well, and a sharp subject on a soft background can score low. Scores are most reliable when comparing similar shots, which is what `cull group` does.
- **Noise raises the sharpness score.** Compare photos taken at a similar ISO.
- **Sharpness can't see small images fairly.** Photos under 1024px are listed separately.
- **Clipping can't reliably catch underexposure.** Very dark photos are listed separately to check by eye, because they look the same as real night scenes. Photos about 1 stop under can still rank well.
- **RAW exposure is read from the preview.** Highlights that look blown there may still be recoverable from the RAW data.
- **Photos without a capture date** can only be matched as duplicates.
- **HEIC, WebP, and AVIF files aren't analyzed yet.**

## Project Structure

```
src/cull/
├── cli.py          Command-line entry point and reports
├── analyze.py      Opens photos, reads EXIF data, runs every measurement
├── sharpness.py    Laplacian-based sharpness scoring
├── exposure.py     Histogram clipping detection
├── similarity.py   Perceptual hashing
├── grouping.py     Burst, retake, and duplicate clustering
├── picks.py        Suggested picks and the reasons for them
├── folders.py      Group folder output
└── cache.py        SQLite cache
```

## Tech Stack

| Area | Tools |
| --- | --- |
| Image analysis | Pillow, NumPy |
| RAW files | rawpy |
| Storage | SQLite |
| Terminal output | colorama |
| Packaging | uv |

## Roadmap

### v0.1 – Core analysis
- [x] Folder scanning and EXIF reading
- [x] RAW preview extraction
- [x] Sharpness and exposure scoring
- [x] SQLite result cache
- [x] Burst and duplicate grouping
- [x] Command-line report

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
- [ ] Package index release

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
