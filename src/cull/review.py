# Builds what the review screen shows and keeps the photographer's decisions, neither touches a photo
import json
import os
from collections import Counter
from dataclasses import dataclass
from threading import Lock
from cull.analyze import beats
from cull.grouping import group_photos
from cull.picks import choose

VERSION = 1 # Of the decisions file
CHOICES = {"pick", "reject"}


class ReviewError(Exception):
    pass


@dataclass
class Shoot:
    folder: object
    names: list # A photo's id is its place in this list, the browser never sends a path
    sections: list


# A file name doesn't have to be valid text, but everything sent to the browser does
def readable(text):
    return text.encode("utf-8", "replace").decode("utf-8")


# Everything the browser needs to know about the groups, in the order they're reviewed
def build_shoot(folder, photos, config):
    long_edge = config.scoring.long_edge
    comparable = sorted(photo.sharpness for photo in photos if photo.long_edge >= long_edge)
    groups, singles = group_photos(photos, config.grouping)
    names = []

    def card(photo, reason=""):
        names.append(photo.name)
        return {"id": len(names) - 1, "name": readable(photo.name), "reason": readable(reason),
                "sharpness": photo.sharpness, "clipped": photo.clipped, "taken": photo.taken,
                "beats": beats(comparable, photo) if photo.long_edge >= long_edge else None}

    sections = []
    for group in groups:
        pick, reasons = choose(group, config.picks, long_edge)
        cards = [card(photo, reasons[photo.name]) for photo in group.photos]
        sections.append({"kind": group.kind, "suggested": cards[group.photos.index(pick)]["id"], "photos": cards})

    # Nothing to compare these with, so there's no suggestion
    if singles:
        cards = [card(photo) for photo in sorted(singles, key=lambda photo: photo.name)]
        sections.append({"kind": "No similar shots", "suggested": None, "photos": cards})

    return Shoot(folder.resolve(), names, sections)


# Beside the shoot like the group folders, a cache can be deleted but this is the photographer's work
def review_file(folder, settings):
    folder = folder.resolve()
    return folder.with_name(folder.name + settings.suffix)


class Decisions:
    def __init__(self, path):
        self.path = path
        self.lock = Lock()
        self.saved = self.read() # Keeps photos that aren't in this run, a config change can hide them for a while

        if not os.access(path.parent, os.W_OK):
            raise ReviewError(f"Can't save decisions to {path}, that folder is read only")

    # A damaged file stops the run, carrying on would replace hours of decisions with an empty list
    def read(self):
        try:
            with open(self.path, encoding="utf-8") as file:
                saved = json.load(file)["decisions"]
            if not set(saved.values()) <= CHOICES:
                raise ValueError("unknown decision")
            return saved
        except FileNotFoundError:
            return {}
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
            raise ReviewError(f"Can't read {self.path}: {e}, fix or move the file and try again")

    # Written to a second file first, so a crash halfway can't leave half a file behind
    def write(self):
        spare = self.path.with_name(self.path.name + ".tmp")
        with open(spare, "w", encoding="utf-8") as file:
            json.dump({"version": VERSION, "decisions": self.saved}, file, indent=1, sort_keys=True)
            file.flush()
            os.fsync(file.fileno())
        os.replace(spare, self.path)

    # Takes (name, decision) pairs, a decision of None clears the photo
    def apply(self, changes):
        with self.lock:
            for name, decision in changes:
                if decision:
                    self.saved[name] = decision
                else:
                    self.saved.pop(name, None)
            self.write()

    def count(self, names):
        return Counter(self.saved[name] for name in names if name in self.saved)
