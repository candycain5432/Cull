# Opens each photo once, measures everything, and remembers the results
import io
import warnings
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime
from fnmatch import fnmatch
from functools import cached_property
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import Base, IFD
import rawpy
from cull import cache
from cull.config import scoring_key
from cull.exposure import exposure
from cull.sharpness import sharpness
from cull.similarity import phash

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


# Sharpness is relative, so it's shown as the % of this shoot a photo beats
def beats(comparable, photo):
    return bisect_left(comparable, photo.sharpness) / max(1, len(comparable) - 1) * 100


# Pillow warns at this many pixels and refuses at double, so half of the setting is the real limit
def set_pixel_limit(megapixels):
    Image.MAX_IMAGE_PIXELS = megapixels * 1_000_000 // 2
    warnings.simplefilter("ignore", Image.DecompressionBombWarning) # It would print over the progress bar


# Every file in a shoot that the config doesn't ignore
def find_files(folder, settings):
    found = []
    for file in sorted(folder.rglob("*") if settings.recursive else folder.iterdir()):
        parts = file.relative_to(folder).parts
        if settings.skip_hidden and any(part.startswith(".") for part in parts):
            continue
        if any(fnmatch(part, pattern) for part in parts for pattern in settings.ignore):
            continue
        if file.is_file():
            found.append(file)
    return found


# Opens a photo for analysis, RAWs use their embedded preview
def open_image(file, raw_extensions):
    if file.suffix.lower() not in raw_extensions:
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
def measure(file, config):
    try:
        with open_image(file, config.files.raw_extensions) as image:
            blown, crushed, brightness = exposure(image, config.scoring)
            exif = image.getexif()
            return {
                "long_edge": max(image.size),
                "sharpness": sharpness(image, config.scoring.long_edge),
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
def analyze_folder(folder, config, ui):
    with ui.working("Finding photos"):
        files = find_files(folder, config.files)

    extensions = config.files.image_extensions | config.files.raw_extensions
    wanted = [file for file in files if file.suffix.lower() in extensions]
    scoring = scoring_key(config.scoring)
    results = {}
    todo = []

    db = cache.connect(config.cache, ui.warn)
    for file in wanted:
        stat = file.stat()
        key = (str(file.resolve()), stat.st_size, stat.st_mtime_ns, scoring)
        results[file] = cache.lookup(db, *key)
        if results[file] is None:
            todo.append((file, key))

    # Cached photos are done first, so the time left only counts the photos that need opening
    with ui.progress("Analyzing", len(todo)) as step:
        for file, key in todo:
            results[file] = measure(file, config)
            cache.store(db, *key, results[file])
            step(file.name)
    db.close()

    photos = []
    skipped = []
    for file in wanted:
        error = results[file].pop("error", None)
        if error:
            skipped.append((file.name, error))
        else:
            photos.append(Photo(name=str(file.relative_to(folder)), **results[file]))

    return photos, skipped, len(files) - len(wanted), len(todo)
