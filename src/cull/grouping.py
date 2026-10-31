# Groups bursts, retakes and duplicates, every link between photos needs one of the rules below
from dataclasses import dataclass
import numpy as np
from cull.similarity import distance

BURST_GAP = 1 # Seconds, same camera this close is one burst even if the subject moved a lot
SCENE_GAP = 30 # Seconds, same camera this close is a retake if the photos also look alike
SIMILAR = 14 # Hash bits, a small reframe or exposure change stays under this
DUPLICATE = 4 # Hash bits, the same picture resized or recompressed stays under this


@dataclass
class Group:
    kind: str
    photos: list


# True if every photo in the list looks like the same picture
def all_duplicates(photos):
    if any(photo.phash is None for photo in photos):
        return False
    hashes = np.array([int(photo.phash, 16) for photo in photos], dtype=np.uint64)
    return all(distance(hash_a, hashes).max() <= DUPLICATE for hash_a in hashes)


# Names the group, a copy either lost its date or shares it, otherwise look-alikes are separate shots
def group_kind(photos):
    times = sorted(photo.when for photo in photos if photo.when)
    gaps = [(b - a).total_seconds() for a, b in zip(times, times[1:])]
    timed = len(times) == len(photos) and len({photo.camera for photo in photos}) == 1

    if all_duplicates(photos) and (not timed or sum(gaps) == 0):
        return "Duplicates"
    return "Burst" if timed and max(gaps) <= BURST_GAP else "Similar shots"


# True if two look-alike photos could be copies, different dates mean two different photos
def could_be_copies(a, b):
    return not a.when or not b.when or abs((a.when - b.when).total_seconds()) <= BURST_GAP


# Splits photos into groups of two or more and the singles left over
def group_photos(photos):
    parent = list(range(len(photos)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def link(i, j):
        parent[find(i)] = find(j)

    hashed = [i for i, photo in enumerate(photos) if photo.phash]
    hashes = np.array([int(photos[i].phash, 16) for i in hashed], dtype=np.uint64)
    bits = dict(zip(hashed, hashes))

    # Burst and retake rules, walks each camera's photos in time order
    timed = sorted((i for i, photo in enumerate(photos) if photo.when), key=lambda i: (photos[i].camera, photos[i].when))
    for place, i in enumerate(timed):
        for j in timed[place + 1:]:
            if photos[i].camera != photos[j].camera:
                break
            gap = (photos[j].when - photos[i].when).total_seconds()
            if gap > SCENE_GAP:
                break
            looks_alike = i in bits and j in bits and distance(bits[i], bits[j]) <= SIMILAR
            if gap <= BURST_GAP or looks_alike:
                link(i, j)

    # Duplicate rule, ignores the camera name since a RAW and its JPEG can spell it differently
    for place, i in enumerate(hashed):
        for offset in np.flatnonzero(distance(hashes[place], hashes[place + 1:]) <= DUPLICATE):
            j = hashed[place + 1 + int(offset)]
            if could_be_copies(photos[i], photos[j]):
                link(i, j)

    members = {}
    for i, photo in enumerate(photos):
        members.setdefault(find(i), []).append(photo)

    groups, singles = [], []
    for found in members.values():
        if len(found) == 1:
            singles.append(found[0])
            continue
        found.sort(key=lambda photo: (photo.taken or "", photo.name))
        groups.append(Group(group_kind(found), found))

    groups.sort(key=lambda group: (group.photos[0].taken or "", group.photos[0].name))
    return groups, singles
