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
        pathreject = args.folder + "/" + "Rejects"
        pathpng = args.folder + "/" + "png"
        pathjpg = args.folder + "/" + "jpg" 
        pathjpeg = args.folder + "/" + "jpeg"
        pathgif = args.folder + "/" + "gif"
        pathbmp = args.folder + "/" + "bmp" 
        pathtiff = args.folder + "/" + "tiff"
        pathtif = args.folder + "/" + "tif"
        pathwebp = args.folder + "/" + "webp" 
        pathavif = args.folder + "/" + "avif"
        pathheic = args.folder + "/" + "heic" 



        if not os.path.exists(pathpng):
            os.mkdir(pathpng)
        if not os.path.exists(pathjpg):
            os.mkdir(pathjpg)
        if not os.path.exists(pathreject):
            os.mkdir(pathreject)
        if not os.path.exists(pathjpeg):
            os.mkdir(pathjpeg)
        if not os.path.exists(pathgif):
            os.mkdir(pathgif)
        if not os.path.exists(pathbmp):
            os.mkdir(pathbmp)
        if not os.path.exists(pathtiff):
            os.mkdir(pathtiff)
        if not os.path.exists(pathtif):
            os.mkdir(pathtif)
        if not os.path.exists(pathwebp):
            os.mkdir(pathwebp)
        if not os.path.exists(pathavif):
            os.mkdir(pathavif)
        if not os.path.exists(pathheic):
            os.mkdir(pathheic)













        for file in os.listdir(args.folder):
            root, extension = os.path.splitext(file)   
            
            if extension == ".png":
                png = args.folder + file
                dest = shutil.move(png, pathpng)
            elif extension == ".jpg":
                jpg = args.folder + file
                dest1 = shutil.move(jpg, pathjpg)
            elif extension == ".jpeg":
                png = args.folder + file
                dest = shutil.move(png, pathjpeg)
            elif extension == ".gif":
                jpg = args.folder + file
                dest1 = shutil.move(jpg, pathgif)
            elif extension == ".bmp":
                png = args.folder + file
                dest = shutil.move(png, pathbmp)
            elif extension == ".tiff":
                jpg = args.folder + file
                dest1 = shutil.move(jpg, pathtiff)
            elif extension == ".tif":
                png = args.folder + file
                dest = shutil.move(png, pathtif)
            elif extension == ".webp":
                jpg = args.folder + file
                dest1 = shutil.move(jpg, pathwebp)
            elif extension == ".avif":
                png = args.folder + file
                dest = shutil.move(png, pathavif)
            elif extension == ".heic":
                jpg = args.folder + file
                dest1 = shutil.move(jpg, pathheic)






    elif args.command == "scan":
        print(f"Scanning {args.folder}...")
        
        for file in os.listdir(args.folder):
            root, extension = os.path.splitext(file)   
            
            if extension == ".jpg":
                print(f"Found image file {file}")
    else:
        parser.print_help()
