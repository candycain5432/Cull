# Perceptual hash: a 64 bit fingerprint that stays nearly the same for similar images
import numpy as np
from PIL import Image, ImageOps
from cull.sharpness import to_gray

HASH_SIZE = 32 # Images shrink to this before hashing, anything smaller has nothing to compare
BASIS = np.cos(np.pi * np.outer(np.arange(HASH_SIZE), 2 * np.arange(HASH_SIZE) + 1) / (2 * HASH_SIZE)) # DCT


# Keeps the coarse shapes of the picture and ignores fine detail, so blur and noise don't change it
def phash(image):
    if max(image.size) < HASH_SIZE:
        return None
    upright = ImageOps.exif_transpose(image) # So a rotated copy still matches
    small = np.asarray(to_gray(upright).resize((HASH_SIZE, HASH_SIZE), Image.Resampling.BOX), dtype=np.float64)
    coarse = (BASIS @ small @ BASIS.T)[:8, :8]
    return np.packbits(coarse > np.median(coarse)).tobytes().hex()


# How many bits differ between one hash and an array of others, 0 means they match
def distance(hash_a, hashes):
    return np.bitwise_count(hash_a ^ hashes)
