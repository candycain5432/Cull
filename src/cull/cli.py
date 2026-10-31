# Importing Modules
import argparse
import os
import shutil
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS, IFD
from colorama import Fore, Style, just_fix_windows_console
from importlib.metadata import version
import io
import sys
import rawpy
from bisect import bisect_left
from cull.analyze import IMAGE_EXTS, RAW_EXTS, UNREADABLE, analyze_folder
from cull.exposure import DARK
from cull.folders import output_folder, write_folders
from cull.grouping import group_photos
from cull.picks import choose
from cull.sharpness import LONG_EDGE

# Prints the line at the end of every report
def print_summary(photos, skipped_bad, skipped_ext, fresh):
    print(f"\n{len(photos)} scored, {skipped_bad} unreadable, {skipped_ext} ignored by extension, {fresh} newly analyzed")

# Entry point, stopping a long scan is normal so it shouldn't print a traceback
def main():
    try:
        run()
    except KeyboardInterrupt:
        print("\nStopped, photos analyzed so far are saved in the cache")
        sys.exit(130)

# Main function
def run():
    just_fix_windows_console() # So the colors work in older Windows terminals
    sys.stdout.reconfigure(errors="replace") # So an odd file name can't crash a report

    # Adds the commands like --help and sort etc
    parser = argparse.ArgumentParser(prog="cull", description="Photo culling assistant",)
    parser.add_argument("--version", action="version", version=f"cull {version('cull')}")
    sub = parser.add_subparsers(dest="command")
    
    scan = sub.add_parser("scan", help="Print the EXIF data of every photo") # Adds <scan> command 
    sorter = sub.add_parser("sort", help="sort the photos into folders based on file extension") # Adds <sort> command
    sharp = sub.add_parser("sharpness", help="Rank photos from sharpest to blurriest") # Adds <sharpness> command
    expose = sub.add_parser("exposure", help="Rank photos from best to worst exposed") # Adds <exposure> command
    score = sub.add_parser("score", help="Show every score for every photo") # Adds <score> command
    grouper = sub.add_parser("group", help="Group similar shots and suggest the best of each") # Adds <group> command
    sorter.add_argument("folder", help="path to the shoot")
    scan.add_argument("folder", help="Path to the shoot")
    sharp.add_argument("folder", help="Path to the shoot")
    expose.add_argument("folder", help="Path to the shoot")
    score.add_argument("folder", help="Path to the shoot")
    grouper.add_argument("folder", help="Path to the shoot")

    args = parser.parse_args()

    # A typo in the path should be an error, <sort> would create the folder otherwise
    if args.command and not os.path.isdir(args.folder):
        parser.error(f"{args.folder} is not a folder")
    
    

# Don't you guys love coding? you won't once you read the code below


    # Sorts all the files in the folder
    if args.command == "sort":
        print(f"Sorting {args.folder}...")
        
        extensions = ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp", "avif", "heic", "cr2", "cr3", "nef", "arw", "dng", "orf", "rw2", "raf"] # List for allowed file types (There will be a option to add to this in the cli)
        
        # Creates folder inside target folder for each file type in list
        for ext in extensions:
            os.makedirs(os.path.join(args.folder, ext), exist_ok=True) # Error avoidence
        
        # Creates a "Rejects" folder for files that dont have the file types in the list
        pathreject = os.path.join(args.folder, "Rejects")
        os.makedirs(pathreject, exist_ok=True)

        # looks at every file
        for file in os.listdir(args.folder):
            src = os.path.join(args.folder, file) # Full path of current entry

            if not os.path.isfile(src):
                continue
            
            # Split the filename
            root, extension = os.path.splitext(file)
            ext = extension.lower().lstrip(".") # Fixes cace sensitivity
        
            # Choses the destination
            if ext in extensions:
                dest = os.path.join(args.folder, ext)
            else:
                dest = pathreject
            
            # Move the file, this refuses to overwrite one that's already there
            try:
                shutil.move(src, dest)
            except shutil.Error as e:
                print(f"Skipping {file}: {e}")


    

    # Scans folders and prints EXIF data
    elif args.command == "scan":
        def read_exif(file):
            if file.suffix.lower() in RAW_EXTS:
                with rawpy.imread(str(file)) as raw:
                    thumb = raw.extract_thumb()
                if thumb.format != rawpy.ThumbFormat.JPEG:
                    raise OSError("Raw thumbnail is not a JEPG, no EXIF avail")
                with Image.open(io.BytesIO(thumb.data)) as image:
                    return collect_exif(image.getexif())
            with Image.open(file) as image:
                return collect_exif(image.getexif())

        def collect_exif(exif):
            out = {}
            for tag_id, value in exif.items():
                out[TAGS.get(tag_id, tag_id)] = value
            for tag_id, value in exif.get_ifd(IFD.Exif).items():
                out[TAGS.get(tag_id, tag_id)] = value
            for tag_id, value in exif.get_ifd(IFD.GPSInfo).items():
                out[GPSTAGS.get(tag_id, tag_id)] = value
            return out



        print(f"Scanning {args.folder}...")
        folder = Path(args.folder) # Turns string into path       
        
        # Counters for the summary at the end
        scanned = skipped_ext = skipped_bad = 0
        
        for file in folder.rglob("*"): # Recursive Scan
            if not file.is_file(): # Skips folders we want files
                continue

            # Skips anything that is not a image (from list)
            if file.suffix.lower() not in IMAGE_EXTS | RAW_EXTS:
                skipped_ext += 1
                continue
            
            # Prints file name in a green header
            print(Fore.GREEN + f"\n === {file.name} ===" + Style.RESET_ALL)

            try:

                exifdata = read_exif(file)
                for tag, data in exifdata.items():
                    if tag in ("ExifOffset", "GPSInfo"):
                        continue
                    if isinstance(data, bytes):
                        try:
                            text = data.decode("utf-8")
                        except UnicodeDecodeError:
                            text = None
                        data = text if text and text.isprintable() else f"<{len(data)} bytes>"



                    print(f"{tag!s:25}: {data}")

                scanned += 1
            
            # Corrupt, empty or fake image files end up here
            except UNREADABLE as e:
                print(f"Skipping {file.name}: {e}")
                skipped_bad += 1
        
        # Summary
        print(f"\n{scanned} scanned, {skipped_bad} unreadable, {skipped_ext} ignored by extension")



    # Ranks photos from sharpest to blurriest
    elif args.command == "sharpness":
        print(f"Scoring {args.folder}...")
        photos, skipped_bad, skipped_ext, fresh = analyze_folder(Path(args.folder))

        ranked = [photo for photo in photos if photo.long_edge >= LONG_EDGE]
        too_small = [photo for photo in photos if photo.long_edge < LONG_EDGE]

        print(Fore.GREEN + "\n === Sharpest to blurriest ===" + Style.RESET_ALL)
        for rank, photo in enumerate(sorted(ranked, key=lambda photo: photo.sharpness, reverse=True), 1):
            print(f"{rank:4}. {photo.sharpness:10.2f}  {photo.name}")

        # Small images score too high, so they can't be compared with the ranking above
        if too_small:
            print(Fore.YELLOW + f"\n === Under {LONG_EDGE}px, not comparable with the ranking above ===" + Style.RESET_ALL)
            for photo in sorted(too_small, key=lambda photo: photo.sharpness, reverse=True):
                print(f"      {photo.sharpness:10.2f}  {photo.name}")

        print_summary(photos, skipped_bad, skipped_ext, fresh)



    # Ranks photos from best to worst exposed
    elif args.command == "exposure":
        print(f"Scoring {args.folder}...")
        photos, skipped_bad, skipped_ext, fresh = analyze_folder(Path(args.folder))

        ranked = [photo for photo in photos if photo.brightness >= DARK]
        dark = [photo for photo in photos if photo.brightness < DARK]

        def print_row(label, photo):
            print(f"{label:>5} {photo.clipped:7.2f}% {photo.blown:7.2f}% {photo.crushed:8.2f}% {photo.brightness:6.0f}  {photo.name}")

        print(Fore.GREEN + "\n === Best to worst exposed ===" + Style.RESET_ALL)
        print(f"{'':5} {'clipped':>8} {'blown':>8} {'crushed':>9} {'bright':>6}")
        for rank, photo in enumerate(sorted(ranked, key=lambda photo: (photo.clipped, photo.name)), 1):
            print_row(f"{rank}.", photo)

        # Underexposed photos and real night scenes look the same, so these aren't ranked
        if dark:
            print(Fore.YELLOW + "\n === Very dark, could be underexposed or a night scene, check by eye ===" + Style.RESET_ALL)
            for photo in sorted(dark, key=lambda photo: photo.brightness):
                print_row("", photo)

        print_summary(photos, skipped_bad, skipped_ext, fresh)



    # Shows every category side by side
    elif args.command == "score":
        print(f"Scoring {args.folder}...")
        photos, skipped_bad, skipped_ext, fresh = analyze_folder(Path(args.folder))

        # Sharpness is relative, so it's shown as the % of this shoot a photo beats
        comparable = sorted(photo.sharpness for photo in photos if photo.long_edge >= LONG_EDGE)

        print(Fore.GREEN + "\n === Scores ===" + Style.RESET_ALL)
        print(f"{'sharp':>10} {'beats':>6} {'clipped':>8} {'blown':>8} {'crushed':>8} {'bright':>6}  {'note':5}  photo")
        for photo in sorted(photos, key=lambda photo: photo.name):
            small = photo.long_edge < LONG_EDGE
            beats = "-" if small else f"{bisect_left(comparable, photo.sharpness) / max(1, len(comparable) - 1) * 100:.0f}%"
            note = "small" if small else "dark" if photo.brightness < DARK else ""
            print(f"{photo.sharpness:10.2f} {beats:>6} {photo.clipped:7.2f}% {photo.blown:7.2f}% {photo.crushed:7.2f}% {photo.brightness:6.0f}  {note:5}  {photo.name}")

        print_summary(photos, skipped_bad, skipped_ext, fresh)



    # Groups similar shots and suggests the best of each
    elif args.command == "group":
        print(f"Grouping {args.folder}...")
        photos, skipped_bad, skipped_ext, fresh = analyze_folder(Path(args.folder))
        groups, singles = group_photos(photos)
        decided = []

        for group in groups:
            pick, reasons = choose(group)
            decided.append((group, pick))
            width = max(len(photo.name) for photo in group.photos)

            print(Fore.GREEN + f"\n === {group.kind}, {len(group.photos)} photos ===" + Style.RESET_ALL)
            print(f"PICK  {pick.name:{width}}  {reasons[pick.name]}")
            for photo in group.photos:
                if photo is not pick:
                    print(f"      {photo.name:{width}}  {reasons[photo.name]}")

        # Nothing to compare these with, so there's no decision to make
        if singles:
            print(Fore.YELLOW + f"\n === No similar shots, {len(singles)} photos ===" + Style.RESET_ALL)
            for photo in sorted(singles, key=lambda photo: photo.name):
                print(f"      {photo.name}")

        print(f"\n{len(groups)} groups, {len(singles)} singles")
        print_summary(photos, skipped_bad, skipped_ext, fresh)

        # Never overwrites old folders, the photographer may have sorted through them
        output = output_folder(Path(args.folder))
        if output.exists():
            print(f"{output} already exists, delete it to rebuild the folders")
        elif photos:
            try:
                write_folders(Path(args.folder), decided, singles)
                print(f"Folders written to {output}")
            except OSError as e:
                print(f"Couldn't write the folders: {e}")



    else:
        parser.print_help()
