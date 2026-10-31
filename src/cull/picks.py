# Suggests the best frame in a group and gives a plain reason for every decision

# Returns the suggested pick and a {name: reason} dict covering every photo in the group
def choose(group, rules, long_edge):
    # Sharpness only compares fairly at the same size, so small copies drop out first
    min_edge = min(long_edge, max(photo.long_edge for photo in group.photos))
    sized = [photo for photo in group.photos if photo.long_edge >= min_edge]

    # Blown or crushed detail can't be fixed later, so it counts before sharpness
    max_clipped = min(photo.clipped for photo in sized) + rules.clip_margin
    clean = [photo for photo in sized if photo.clipped <= max_clipped]

    pick = max(clean, key=lambda photo: (photo.sharpness, photo.long_edge))
    reasons = {pick.name: pick_reason(pick, sized, clean, max_clipped, rules)}
    for photo in group.photos:
        if photo is not pick:
            reasons[photo.name] = reject_reason(photo, pick, min_edge, max_clipped, rules)
    return pick, reasons


# Percent by which a is less sharp than b
def sharpness_lost(a, b):
    return (1 - a.sharpness / b.sharpness) * 100 if b.sharpness else 0


def pick_reason(pick, sized, clean, max_clipped, rules):
    rivals = [photo for photo in clean if photo is not pick]

    if rivals:
        runner_up = max(rivals, key=lambda photo: photo.sharpness)
        lost = sharpness_lost(runner_up, pick)
        if lost < rules.same_sharpness:
            reason = f"Ties {runner_up.name} on sharpness"
        else:
            reason = f"Sharpest, next best is {runner_up.name} at {lost:.0f}% less sharp"
    elif len(sized) > 1:
        reason = f"Least clipped at {pick.clipped:.1f}%"
    else:
        reason = f"Largest copy at {pick.long_edge}px"

    # Mentions the frame it beat on exposure, so the choice doesn't look like a mistake
    sharper = [photo for photo in sized if photo.clipped > max_clipped and photo.sharpness > pick.sharpness]
    if sharper:
        best = max(sharper, key=lambda photo: photo.sharpness)
        reason += f", {best.name} is sharper but {best.clipped:.1f}% clipped against {pick.clipped:.1f}%"
    return reason


def reject_reason(photo, pick, min_edge, max_clipped, rules):
    if photo.long_edge < min_edge:
        return f"Only {photo.long_edge}px, the pick is {pick.long_edge}px"
    if photo.clipped > max_clipped:
        return f"{photo.clipped:.1f}% clipped, the pick is {pick.clipped:.1f}%"

    lost = sharpness_lost(photo, pick)
    if lost < rules.same_sharpness:
        return "Same sharpness as the pick"
    return f"{lost:.0f}% less sharp than the pick"
