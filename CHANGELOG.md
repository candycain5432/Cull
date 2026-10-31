# Changelog

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
