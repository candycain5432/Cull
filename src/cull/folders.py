# Lays groups out as folders beside the shoot, the originals never move
import os
import shutil


# Beside the shoot rather than inside it, or every later scan would count each photo twice
def output_folder(folder):
    folder = folder.resolve()
    return folder.with_name(f"{folder.name}_groups")


# A hard link is a second name for the same file, so it takes no extra disk space
def place(source, target):
    try:
        os.link(source, target)
    except OSError: # Memory cards and some drives can't do hard links
        shutil.copy2(source, target)


# Two cards can both have an IMG_0001.jpg, so nested photos keep their folder in the name
def target_for(folder, name, prefix=""):
    flat = prefix + name.replace(os.sep, "__")
    target = folder / flat
    number = 2
    while target.exists():
        target = folder / f"{number}_{flat}"
        number += 1
    return target


# Takes (group, pick) pairs and the singles, the pick in each folder starts with PICK_
def write_folders(folder, decided, singles):
    output = output_folder(folder)
    output.mkdir()

    for number, (group, pick) in enumerate(decided, 1):
        group_folder = output / f"{number:03}_{group.kind.lower().replace(' ', '_')}"
        group_folder.mkdir()
        for photo in group.photos:
            prefix = "PICK_" if photo is pick else ""
            place(folder / photo.name, target_for(group_folder, photo.name, prefix))

    if singles:
        single_folder = output / "singles"
        single_folder.mkdir()
        for photo in singles:
            place(folder / photo.name, target_for(single_folder, photo.name))

    return output
