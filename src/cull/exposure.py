# Exposure score: how much of the frame is clipped, lower means more detail survived
import numpy as np
from cull.sharpness import downscale, to_gray


# Three channels, 16 bit images go through to_gray so they don't clip to white
def to_rgb(image):
    if image.mode.startswith("I"):
        return to_gray(image).convert("RGB")
    return image.convert("RGB")


# Returns the % of pixels blown, the % crushed, and the average brightness (0 to 255)
# Blown looks at any channel, grayscale would miss a clipped red sunset
# Crushed needs all channels low, one low channel is just a saturated color
def exposure(image, scoring):
    small = downscale(to_rgb(image), scoring.long_edge)
    brightest = np.asarray(small).max(axis=2)
    blown = float((brightest >= scoring.blown).mean() * 100)
    crushed = float((brightest <= scoring.crushed).mean() * 100)
    return blown, crushed, float(np.asarray(small.convert("L")).mean())
