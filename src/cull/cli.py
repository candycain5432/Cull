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

RAW_EXTS = {".cr2", ".cr3", ".nef", ".arw", ".dng", ".orf", ".rw2", ".raf"}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

# Main function
def main():
    
    # Adds the commands like --help and sort etc
    parser = argparse.ArgumentParser(prog="cull", description="Photo culling assistant",)
    sub = parser.add_subparsers(dest="command")
    
    scan = sub.add_parser("scan", help="Analyze a folder of photos") # Adds <scan> command 
    sorter = sub.add_parser("sort", help="sort the photos into folders based on file extension") # Adds <sort> command
    sorter.add_argument("folder", help="path to the shoot") 
    scan.add_argument("folder", help="Path to the shoot")

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
        


    else:
        parser.print_help()
