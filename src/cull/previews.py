# Turns a photo into something a browser can show, RAWs use their embedded preview
import io
from PIL import Image, ImageOps
from PIL.ExifTags import Base
import rawpy
from cull.analyze import open_image
from cull.exposure import to_rgb

BROWSER_READY = {".jpg", ".jpeg", ".png", ".webp"} # Sent as they are, nothing is lost that way
QUALITY = 88

# LibRaw's codes for how the camera was held
TURNS = {3: Image.Transpose.ROTATE_180, 5: Image.Transpose.ROTATE_90, 6: Image.Transpose.ROTATE_270}


# RAW previews often don't say which way up they are, but the RAW itself does
def raw_turn(file):
    with rawpy.imread(str(file)) as raw:
        return TURNS.get(raw.sizes.flip)


def upright(image, file, raw_extensions):
    if file.suffix.lower() in raw_extensions and image.getexif().get(Base.Orientation, 1) == 1:
        turn = raw_turn(file)
        return image.transpose(turn) if turn else image
    return ImageOps.exif_transpose(image)


# Returns a JPEG of the photo, edge is the longest side in pixels and None keeps the full size
def render(file, raw_extensions, edge=None):
    with open_image(file, raw_extensions) as image:
        # A profile only fits the mode it was made for, a CMYK one would ruin the colors of an RGB copy
        profile = image.info.get("icc_profile") if image.mode == "RGB" else None
        if edge:
            image.draft("RGB", (edge, edge)) # A big JPEG can be decoded at a fraction of its size
        picture = to_rgb(upright(image, file, raw_extensions))

    if edge:
        picture.thumbnail((edge, edge))
    buffer = io.BytesIO()
    picture.save(buffer, "JPEG", quality=QUALITY, icc_profile=profile)
    return buffer.getvalue()
