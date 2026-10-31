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
| Review screen | Pick and reject photos in your browser using only the keyboard, with a grid of groups and a side-by-side compare view |
| Group folders | Lays the groups out as folders without moving your originals |
| RAW support | Reads CR2, CR3, NEF, ARW, DNG, ORF, RW2, and RAF files through their embedded previews |
| Instant repeat runs | Results are cached in SQLite, so a second run doesn't reopen any photos |
| Color reports | Tables, score bars, and live progress bars, with five color themes |
| Config file | Change the thresholds, colors, file types, and folder names in one TOML file |

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
- A web browser, for `cull review`
- Developed and tested on Linux. macOS and Windows should work but haven't been tested yet.

## Usage

| Command | What it does |
| --- | --- |
| `cull review ./shoot` | Opens the review screen, see [Reviewing a shoot](#reviewing-a-shoot) |
| `cull group ./shoot` | Groups similar shots, suggests the best of each, and writes the group folders |
| `cull score ./shoot` | Shows every score for every photo |
| `cull sharpness ./shoot` | Ranks photos from sharpest to blurriest |
| `cull exposure ./shoot` | Ranks photos from best to worst exposed |
| `cull scan ./shoot` | Prints the EXIF data of every photo |
| `cull sort ./shoot` | Moves photos into folders by file type |
| `cull config` | Shows the settings in use, see [Configuration](#configuration) |

Every command also takes `--no-color`, `--no-progress`, and `--config FILE`.

`cull group` is the one most people want:

```
$ cull group ./shoot
Cull · Grouping ./shoot

 Burst, 3 photos  ──────────────────────────────────────────────────────
★ PICK  DSC1070.jpg  Sharpest, next best is DSC1069.jpg at 92% less sharp, DSC1071.jpg is sharper but 80.5% clipped against 5.8%
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

If a drive can't do hard links, Cull makes normal copies instead. To choose yourself, set `link` in the `[folders]` section of the config to `symlink` or `copy`. Cull never overwrites an existing `shoot_groups` folder, so delete it to rebuild it.

Sending a report to a file or another program gives plain columns with no colors or borders, so `cull score ./shoot > scores.txt` is easy to search. Cull also follows the `NO_COLOR` environment variable.

## Reviewing a shoot

`cull review` is where you make the final call. It scores and groups the shoot, then opens a grid of every group in your browser with the suggested frame highlighted. Press Ctrl+C in the terminal when you're done.

```bash
cull review ./shoot                # Opens your browser
cull review ./shoot --no-browser   # Only prints the address
cull review ./shoot --port 8000    # Uses a fixed port
```

Everything can be done from the keyboard:

| Key | Grid | Open photo | Compare |
| --- | --- | --- | --- |
| Arrow keys | Move | Previous or next photo | Change the right photo |
| `P` / `X` | Pick / reject | Pick / reject | Pick / reject the right photo |
| `U` | Clear the decision | Clear the decision | Clear the right photo |
| `A` | Accept the group | Accept the group | Pick the left photo, reject the rest |
| `Tab` / `Shift+Tab` | Next / previous group | Next / previous group | Next / previous group |
| `N` | Next undecided photo | Next undecided photo | Next undecided photo |
| `Enter` | Open the photo | Back to the grid | Back to the grid |
| `C` | Compare | Compare | Back to one photo |
| `S` | | | Move the right photo to the left |
| `Z` | | Zoom to 100% | Zoom to 100% |
| `Shift` + arrow keys | | Pan | Pan both photos |
| `Esc` | | Back to the grid | Back to the grid |
| `Ctrl+Z` | Undo | Undo | Undo |

Pressing `P` or `X` a second time takes the decision back. `A` is the fast path through a shoot: it picks the suggested frame and rejects everything else in the group, but it never changes a decision you've already made. It doesn't work on the "No similar shots" section, because those photos have nothing in common.

To choose between frames by hand, press `C`. The suggested frame starts on the left, and the arrow keys change the photo on the right. When the right one is better, press `S` to move it to the left, then press `A` to keep whichever photo finished on the left.

Decisions save as you make them, to a file beside the shoot called `shoot_review.json`, so you can stop and carry on later. Rejecting a photo only records the decision, nothing is moved or deleted. Other photo apps can't read this file yet, that comes with XMP export in v0.4.

The review screen is only reachable from your own computer.

## Configuration

Colors, progress bars, scoring thresholds, grouping rules, folder names, and file types can all be changed without touching the code.

```bash
cull config init     # Creates the config file, with every setting explained
cull config show     # Lists the settings in use and what you've changed
cull config themes   # Previews the color themes
cull config path     # Prints where the config file is
```

The file lives at `~/.config/cull/config.toml`, and only needs the settings you want to change:

```toml
[display]
theme = "ocean"
max_rows = 50

[grouping]
scene_gap = 10.0

[folders]
suffix = "_culled"
link = "copy"

[files]
image_extensions = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"]
ignore = ["*_edit.jpg", "Rejects"]
```

| Section | What it changes |
| --- | --- |
| `[display]` | Theme, table style, score bars, decimal places, row limit, and which parts of a report appear |
| `[progress]` | Bar or spinner, its width, and which details it shows |
| `[highlight]` | The scores at which report colors change |
| `[colors]` | Any single color of the theme |
| `[scoring]` | Sharpness size, blown and crushed limits, the dark limit, and the largest image to open |
| `[grouping]` | Burst and retake time gaps, and how alike two photos have to be |
| `[picks]` | How much extra clipping rules out a frame, and what counts as a tie |
| `[folders]` | Output folder names, the pick marker, and hard links, symlinks, or copies |
| `[review]` | Port, opening the browser, moving on after a decision, thumbnail size, and the decisions file name |
| `[files]` | File types, subfolders, hidden files, and names to ignore |
| `[sort]` | The folders `cull sort` creates |
| `[scan]` | EXIF tags to hide, including location data |
| `[cache]` | Turns the cache off, or moves it |

To use a different file, pass `--config FILE` or set the `CULL_CONFIG` environment variable. A misspelled setting prints a warning and is ignored, and a value that can't work stops the run with a list of what's wrong.

Changing `long_edge`, `blown`, `crushed`, or `max_megapixels` changes the scores themselves, so the next run analyzes those photos again.

## How It Works

1. **Read** – Finds every photo in the folder, including subfolders. RAW files use their embedded JPEG preview.
2. **Score** – Measures sharpness, clipped highlights and shadows, and brightness, and reads the capture time and camera from the EXIF data.
3. **Group** – Links photos using three rules:
   - **Burst:** same camera, 1 second apart or less
   - **Similar shots:** same camera, within 30 seconds, and they look alike
   - **Duplicates:** near-identical, with the same capture time or a missing date
4. **Pick** – Within each group, drops undersized copies, then frames with 5 or more points of extra clipping, and picks the sharpest of what's left.

Results are saved to `~/.cache/cull/cache.db`. A photo is only analyzed again if its size, modified time, or scoring settings change. It's safe to delete this file at any time.

## Limitations

- **Sharpness is measured on the whole frame.** A blurred subject on a sharp background can score well, and a sharp subject on a soft background can score low. Scores are most reliable when comparing similar shots, which is what `cull group` does.
- **Noise raises the sharpness score.** Compare photos taken at a similar ISO.
- **Sharpness can't see small images fairly.** Photos under 1024px are listed separately.
- **Clipping can't reliably catch underexposure.** Very dark photos are listed separately to check by eye, because they look the same as real night scenes. Photos about 1 stop under can still rank well.
- **RAW exposure is read from the preview.** Highlights that look blown there may still be recoverable from the RAW data.
- **Photos without a capture date** can only be matched as duplicates.
- **HEIC and AVIF files aren't analyzed yet.** WebP files are skipped by default, add `.webp` to `image_extensions` in the config to include them.

## Project Structure

```
src/cull/
├── cli.py          Command-line entry point and reports
├── ui.py           Colors, tables, and progress bars
├── themes.py       Color themes
├── config.py       Loads and checks the config file
├── default.toml    Every setting and its default value
├── analyze.py      Opens photos, reads EXIF data, runs every measurement
├── sharpness.py    Laplacian-based sharpness scoring
├── exposure.py     Histogram clipping detection
├── similarity.py   Perceptual hashing
├── grouping.py     Burst, retake, and duplicate clustering
├── picks.py        Suggested picks and the reasons for them
├── folders.py      Group folder output
├── cache.py        SQLite cache
├── review.py       What the review screen shows, and saving decisions
├── previews.py     Turns photos into images a browser can show
├── server.py       Local web server for the review screen
└── web/            The review screen itself
```

## Tech Stack

| Area | Tools |
| --- | --- |
| Image analysis | Pillow, NumPy |
| RAW files | rawpy |
| Storage | SQLite |
| Terminal output | Rich |
| Review screen | FastAPI, Uvicorn, plain JavaScript |
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
- [x] Grid view of grouped images
- [x] Keyboard pick/reject controls
- [x] Side-by-side compare view

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
