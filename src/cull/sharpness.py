# Sharpness score: the variance of the Laplacian, higher means sharper
import numpy as np
from PIL import Image


# Grayscale, because sharpness is about brightness edges and color only adds noise
def to_gray(image):
    if image.mode.startswith("I"): # 16 bit images, convert("L") would clip these to white
        return Image.fromarray((np.asarray(image) >> 8).astype(np.uint8))
    return image.convert("L")


# Scores are only comparable at the same size, smaller images are left alone as upscaling would fake the score
def downscale(image, long_edge):
    scale = long_edge / max(image.size)
    if scale >= 1:
        return image
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.Resampling.BOX) # BOX averages pixels like cv2.INTER_AREA


# Same result as cv2.Laplacian(gray, cv2.CV_64F), the border mirrors like OpenCV's default
def laplacian(gray):
    p = np.pad(gray, 1, mode="reflect")
    return p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:] - 4 * p[1:-1, 1:-1]


# Raw score for one PIL image, only meaningful relative to other photos
def sharpness(image, long_edge):
    gray = np.asarray(downscale(to_gray(image), long_edge), dtype=np.float64) # float so negatives don't wrap
    return float(laplacian(gray).var())
