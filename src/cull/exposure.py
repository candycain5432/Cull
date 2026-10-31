# Exposure score: how much of the frame is clipped, lower means more detail survived
import numpy as np
from cull.sharpness import downscale, to_gray

BLOWN = 253 # Any channel this high is blown, grayscale would miss a clipped red sunset
CRUSHED = 5 # All channels this low is black, one low channel is just a saturated color
DARK = 64 # Darker than this on average and clipping alone can't judge the photo


# Three channels, 16 bit images go through to_gray so they don't clip to white
def to_rgb(image):
    if image.mode.startswith("I"):
        return to_gray(image).convert("RGB")
    return image.convert("RGB")


# Returns the % of pixels blown, the % crushed, and the average brightness (0 to 255)
def exposure(image):
    small = downscale(to_rgb(image))
    brightest = np.asarray(small).max(axis=2)
    blown = float((brightest >= BLOWN).mean() * 100)
    crushed = float((brightest <= CRUSHED).mean() * 100)
    return blown, crushed, float(np.asarray(small.convert("L")).mean())
