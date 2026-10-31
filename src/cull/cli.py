# Importing Modules
import argparse
import os
import shutil
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS, GPSTAGS, IFD
from colorama import Fore, Back,Style
import io
import rawpy
from cull.exposure import DARK, exposure
from cull.sharpness import LONG_EDGE, sharpness

RAW_EXTS = {".cr2", ".cr3", ".nef", ".arw", ".dng", ".orf", ".rw2", ".raf"}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

# Opens a photo for analysis, RAWs use their embedded preview
def open_image(file):
    if file.suffix.lower() not in RAW_EXTS:
        return Image.open(file)
    with rawpy.imread(str(file)) as raw:
        thumb = raw.extract_thumb()
    if thumb.format == rawpy.ThumbFormat.JPEG:
        return Image.open(io.BytesIO(thumb.data))
    return Image.fromarray(thumb.data) # Bitmap previews are already pixels

# Runs measure on every photo in a folder, returns the (name, result) pairs and the skip counts
def score_folder(folder, measure):
    results = []
    skipped_ext = skipped_bad = 0

    for file in folder.rglob("*"):
        if not file.is_file():
            continue

        if file.suffix.lower() not in IMAGE_EXTS | RAW_EXTS:
            skipped_ext += 1
            continue

        try:
            with open_image(file) as image:
                results.append((str(file.relative_to(folder)), measure(image)))

        # Corrupt, empty or fake image files end up here
        except (UnidentifiedImageError, OSError, rawpy.LibRawError) as e:
            print(f"Skipping {file.name}: {e}")
            skipped_bad += 1

    return results, skipped_bad, skipped_ext

# Main function
def main():
    
    # Adds the commands like --help and sort etc
    parser = argparse.ArgumentParser(prog="cull", description="Photo culling assistant",)
    sub = parser.add_subparsers(dest="command")
    
    scan = sub.add_parser("scan", help="Analyze a folder of photos") # Adds <scan> command 
    sorter = sub.add_parser("sort", help="sort the photos into folders based on file extension") # Adds <sort> command
    sharp = sub.add_parser("sharpness", help="Rank photos from sharpest to blurriest") # Adds <sharpness> command
    expose = sub.add_parser("exposure", help="Rank photos from best to worst exposed") # Adds <exposure> command
    sorter.add_argument("folder", help="path to the shoot")
    scan.add_argument("folder", help="Path to the shoot")
    sharp.add_argument("folder", help="Path to the shoot")
    expose.add_argument("folder", help="Path to the shoot")

    args = parser.parse_args()
    
    

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
            
            # Move the file
            shutil.move(src, dest)


    

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
            except (UnidentifiedImageError, OSError, rawpy.LibRawError) as e:
                print(f"Skipping {file.name}: {e}")
                skipped_bad += 1
        
        # Summary
        print(f"\n{scanned} scanned, {skipped_bad} unreadable, {skipped_ext} ignored by extension")



    # Ranks photos from sharpest to blurriest
    elif args.command == "sharpness":
        print(f"Scoring {args.folder}...")
        results, skipped_bad, skipped_ext = score_folder(
            Path(args.folder), lambda image: (sharpness(image), max(image.size) < LONG_EDGE))

        ranked = [(score, name) for name, (score, small) in results if not small]
        too_small = [(score, name) for name, (score, small) in results if small]

        print(Fore.GREEN + "\n === Sharpest to blurriest ===" + Style.RESET_ALL)
        for rank, (score, name) in enumerate(sorted(ranked, reverse=True), 1):
            print(f"{rank:4}. {score:10.2f}  {name}")

        # Small images score too high, so they can't be compared with the ranking above
        if too_small:
            print(Fore.YELLOW + f"\n === Under {LONG_EDGE}px, not comparable with the ranking above ===" + Style.RESET_ALL)
            for score, name in sorted(too_small, reverse=True):
                print(f"      {score:10.2f}  {name}")

        # Summary
        print(f"\n{len(results)} scored, {skipped_bad} unreadable, {skipped_ext} ignored by extension")



    # Ranks photos from best to worst exposed
    elif args.command == "exposure":
        print(f"Scoring {args.folder}...")
        results, skipped_bad, skipped_ext = score_folder(Path(args.folder), exposure)

        ranked = [(blown + crushed, blown, crushed, shade, name) for name, (blown, crushed, shade) in results if shade >= DARK]
        dark = [(blown + crushed, blown, crushed, shade, name) for name, (blown, crushed, shade) in results if shade < DARK]

        def print_row(label, photo):
            clipped, blown, crushed, shade, name = photo
            print(f"{label:>5} {clipped:7.2f}% {blown:7.2f}% {crushed:8.2f}% {shade:6.0f}  {name}")

        print(Fore.GREEN + "\n === Best to worst exposed ===" + Style.RESET_ALL)
        print(f"{'':5} {'clipped':>8} {'blown':>8} {'crushed':>9} {'bright':>6}")
        for rank, photo in enumerate(sorted(ranked), 1):
            print_row(f"{rank}.", photo)

        # Underexposed photos and real night scenes look the same, so these aren't ranked
        if dark:
            print(Fore.YELLOW + "\n === Very dark, could be underexposed or a night scene, check by eye ===" + Style.RESET_ALL)
            for photo in sorted(dark, key=lambda photo: photo[3]):
                print_row("", photo)

        # Summary
        print(f"\n{len(results)} scored, {skipped_bad} unreadable, {skipped_ext} ignored by extension")



    else:
        parser.print_help()
