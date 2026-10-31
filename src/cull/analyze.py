# Opens each photo once, measures everything, and remembers the results
import io
import sys
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import Base, IFD
import rawpy
from cull import cache
from cull.exposure import exposure
from cull.sharpness import sharpness
from cull.similarity import phash

RAW_EXTS = {".cr2", ".cr3", ".nef", ".arw", ".dng", ".orf", ".rw2", ".raf"}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

Image.MAX_IMAGE_PIXELS = 300_000_000 # Pillow's default stops at 179MP, phones now shoot 200MP

# Corrupt, empty, fake or impossibly large image files raise one of these
UNREADABLE = (UnidentifiedImageError, Image.DecompressionBombError, OSError, rawpy.LibRawError)


@dataclass
class Photo:
    name: str # Path inside the shoot, two cards can both have an IMG_0001.jpg
    long_edge: int
    sharpness: float
    blown: float
    crushed: float
    brightness: float
    taken: str | None # ISO format, None if the photo has no usable date
    camera: str
    phash: str | None

    @property
    def clipped(self):
        return self.blown + self.crushed

    @cached_property
    def when(self):
        return datetime.fromisoformat(self.taken) if self.taken else None


# Opens a photo for analysis, RAWs use their embedded preview
def open_image(file):
    if file.suffix.lower() not in RAW_EXTS:
        return Image.open(file)
    with rawpy.imread(str(file)) as raw:
        thumb = raw.extract_thumb()
    if thumb.format == rawpy.ThumbFormat.JPEG:
        return Image.open(io.BytesIO(thumb.data))
    return Image.fromarray(thumb.data) # Bitmap previews are already pixels


# Finds when a photo was taken, RAW previews only have DateTime so it falls back through the tags
def read_taken(exif):
    details = exif.get_ifd(IFD.Exif)
    for value, subsec in ((details.get(Base.DateTimeOriginal), details.get(Base.SubsecTimeOriginal)),
                          (details.get(Base.DateTimeDigitized), details.get(Base.SubsecTimeDigitized)),
                          (exif.get(Base.DateTime), details.get(Base.SubsecTime))):
        try:
            taken = datetime.strptime(str(value).strip(" \x00"), "%Y:%m:%d %H:%M:%S")
        except ValueError: # Missing, zeroed or garbage dates
            continue
        digits = str(subsec).strip(" \x00")
        if subsec is not None and digits.isdigit(): # Burst frames are often in the same second
            taken = taken.replace(microsecond=int(digits.ljust(6, "0")[:6]))
        return taken.isoformat()
    return None


# Make and model, some cameras pad these with spaces and null bytes
def read_camera(exif):
    return " ".join(str(exif.get(tag, "")).replace("\x00", "").strip() for tag in (Base.Make, Base.Model)).strip()


# Measures one photo
def measure(file):
    try:
        with open_image(file) as image:
            blown, crushed, brightness = exposure(image)
            exif = image.getexif()
            return {
                "long_edge": max(image.size),
                "sharpness": sharpness(image),
                "blown": blown,
                "crushed": crushed,
                "brightness": brightness,
                "taken": read_taken(exif),
                "camera": read_camera(exif),
                "phash": phash(image),
            }

    except UNREADABLE as e:
        return {"error": str(e)}


# Results for every photo in a folder, only opens the ones the cache hasn't seen
def analyze_folder(folder):
    files = [file for file in sorted(folder.rglob("*")) if file.is_file()]
    wanted = [file for file in files if file.suffix.lower() in IMAGE_EXTS | RAW_EXTS]
    skipped = []
    photos = []
    fresh = 0

    db = cache.connect()
    for count, file in enumerate(wanted, 1):
        stat = file.stat()
        path = str(file.resolve())

        result = cache.lookup(db, path, stat.st_size, stat.st_mtime_ns)
        if result is None:
            result = measure(file)
            cache.store(db, path, stat.st_size, stat.st_mtime_ns, result)
            fresh += 1
            print(f"\rAnalyzing {count}/{len(wanted)}", end="", file=sys.stderr)

        error = result.pop("error", None)
        if error:
            skipped.append((file.name, error))
        else:
            photos.append(Photo(name=str(file.relative_to(folder)), **result))
    db.close()

    if fresh:
        print(file=sys.stderr)
    for name, error in skipped:
        print(f"Skipping {name}: {error}")

    return photos, len(skipped), len(files) - len(wanted), fresh
