# Cull Roadmap

Oct 19, 2026 · @William Cain

## Phase 0: Setup

**Goal:** a clean project skeleton.

- [x] Create the GitHub repo, a virtual environment, and the folder structure
- [x] Set up `pyproject.toml`, `.gitignore`, and a basic README
- [x] Add a minimal `cull` command: a CLI entry point (argparse) registered under `[project.scripts]` in `pyproject.toml`, then install with `pip install -e .`
- [x] Gather 3–5 real shoots to test with, including some intentionally bad shots

**Done when:** `cull --help` runs from your terminal.

## Phase 1: Read the photos

**Goal:** Cull can see your files.

- [ ] Scan a folder for JPEGs and RAW files
- [ ] Read EXIF data (timestamp, shutter, ISO, aperture)
- [ ] Pull the embedded JPEG previews out of RAW files
- [ ] Downscale images for analysis

**Done when:** `cull scan ./shoot` lists every photo with its settings.

## Phase 2: Judge the photos

**Goal:** score each photo's quality.

- [ ] Sharpness (variance of the Laplacian)
- [ ] Exposure (histogram clipping)
- [ ] Save the results to a SQLite cache

**Done when:** a report ranks every photo from sharpest to blurriest, and a second run is instant.

## Phase 3: Group the photos

**Goal:** find bursts and duplicates.

- [ ] Group shots by time gap
- [ ] Compare images with perceptual hashing
- [ ] Pick the best frame in each group
- [ ] Attach a reason to every decision

**Done when:** the report shows groups, each with a suggested pick and an explanation.

**Milestone: v0.1.** It's already useful. Push it, tag a release, and celebrate a little.

## Phase 4: The review screen

**Goal:** humans make the final call.

- [ ] Local web UI (FastAPI plus a browser frontend)
- [ ] Grid of groups with the suggested pick highlighted
- [ ] Keyboard controls: P = pick, X = reject, arrow keys to move
- [ ] Side-by-side compare view

**Done when:** you can cull a full shoot without touching the mouse.

**Milestone: v0.2**

## Phase 5: Get smarter

**Goal:** handle real-world photos.

- [ ] Face detection
- [ ] Measure sharpness on the subject, not the whole frame
- [ ] Blink detection (eye aspect ratio)
- [ ] Use relative thresholds, so dark and moody photos aren't punished

**Done when:** blurred-background portraits stop getting flagged as blurry.

**Milestone: v0.3**

## Phase 6: Play nice with other apps

**Goal:** fit into photographers' workflows.

- [ ] Write XMP sidecar files that Lightroom and darktable can read
- [ ] Optionally move rejects to a `_rejected/` folder
- [ ] Never delete anything, ever

**Done when:** you open the shoot in darktable and your picks are already flagged.

**Milestone: v0.4**

## Phase 7: Prove it works

**Goal:** real numbers for your resume.

- [ ] Hand-label about 1,000+ of your own photos
- [ ] Measure how often Cull agrees with you
- [ ] Tune thresholds against those results

**Done when:** you can state the accuracy in one sentence, with numbers.

## Phase 8: Polish and ship

**Goal:** make it look professional.

- [ ] Use multiprocessing for speed
- [ ] Tests plus GitHub Actions CI
- [ ] Make it installable with `pipx install cull`
- [ ] README with a demo GIF at the top
- [ ] Tag the release on GitHub

**Milestone: v1.0.** Put it on your resume.

## Rule of thumb

Finish each phase before starting the next. Phases 1–3 alone give you a working, useful tool; everything after that is upgrades. A half-finished UI is worth less than a finished CLI.
