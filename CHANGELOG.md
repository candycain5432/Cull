# Changelog

## Unreleased

### Added

- `cull review` opens a review screen in your browser, with a grid of groups and the suggested pick highlighted
- Keyboard controls for the whole review: P to pick, X to reject, arrow keys to move, and A to accept a group in one key
- Side-by-side compare view with 100% zoom, and both sides pan to the same spot
- Review decisions save as they're made to a file beside the shoot, so a review can be stopped and carried on later
- A `[review]` section in the config, and `--port` and `--no-browser` on `cull review`
- Color reports with tables, score bars, and a totals panel
- Live progress bars with the time left, speed, and current file, for analyzing, sorting, and writing group folders
- Five color themes: default, ocean, sunset, colorblind, and mono
- A config file at `~/.config/cull/config.toml`, covering display, progress, colors, scoring, grouping, picks, folders, file types, `cull sort`, `cull scan`, and the cache
- `cull config` to show the settings, create the file, print its path, and preview the themes
- `--config`, `--no-color`, and `--no-progress` on every command
- Group folders can now use symlinks or copies instead of hard links
- WebP photos can be analyzed by adding `.webp` to `image_extensions`

### Changed

- Reports sent to a file or another program are now plain columns, with no color codes
- Narrow terminals leave out the less important columns instead of cutting off scores and names
- Cached results now remember the scoring settings that made them, so the first run after updating analyzes every photo again

### Fixed

- A read-only cache no longer crashes the run, Cull warns and carries on without saving
- Images between 300MP and 600MP no longer print a Pillow warning

## 0.1.0 - 2026-10-31

The first release. Cull can now score a folder of photos, group similar shots, and suggest the best frame in each group.

### Added

- `cull group` groups bursts, retakes, and duplicates, suggests the best frame in each group with a reason for every decision, and writes the groups out as folders without moving your originals
- `cull score` shows every score for every photo
- `cull sharpness` ranks photos from sharpest to blurriest
- `cull exposure` ranks photos from best to worst exposed
- `cull scan` prints the EXIF data of every photo
- `cull sort` moves photos into folders by file type
- `cull --version`
- SQLite cache, so a second run doesn't reopen any photos
- RAW support through embedded previews (CR2, CR3, NEF, ARW, DNG, ORF, RW2, RAF)

### Known limitations

- Sharpness is measured on the whole frame, not on the subject
- Underexposure of about 1 stop is usually missed
- HEIC, WebP, and AVIF files aren't analyzed yet
- Only tested on Linux so far
