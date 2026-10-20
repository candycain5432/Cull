import argparse
import os
import shutil

def main():

    parser = argparse.ArgumentParser(prog="cull", description="Photo culling assistant",)
    sub = parser.add_subparsers(dest="command")
    
    scan = sub.add_parser("scan", help="Analyze a folder of photos")
    sorter = sub.add_parser("sort", help="sort the photos into folders based on file extension")
    sorter.add_argument("folder", help="path to the shoot")
    scan.add_argument("folder", help="Path to the shoot")

    args = parser.parse_args()
    

    if args.command == "sort":
        print(f"Sorting {args.folder}...")
        
        extensions = ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp", "avif", "heic"]
        
        for ext in extensions:
            os.makedirs(os.path.join(args.folder, ext), exist_ok=True)
        pathreject = os.path.join(args.folder, "Rejects")
        os.makedirs(pathreject, exist_ok=True)

        for file in os.listdir(args.folder):
            src = os.path.join(args.folder, file)

            if not os.path.isfile(src):
                continue

            root, extension = os.path.splitext(file)
            ext = extension.lower().lstrip(".")
        
            if ext in extension:
                dest = os.path.join(args.folder, ext)
            else:
                dest = pathreject

            shutil.move(src, dest)


    elif args.command == "scan":
        print(f"Scanning {args.folder}...")
        
        for file in os.listdir(args.folder):
            root, extension = os.path.splitext(file)   
            
            if extension == ".jpg":
                print(f"Found image file {file}")
    else:
        parser.print_help()
