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
        pathr = args.folder + "/" + "Rejects"
        pathp = args.folder + "/" + "png"
        pathj = args.folder + "/" + "jpeg" 
        if not os.path.exists(pathp):
            os.mkdir(pathp)
        if not os.path.exists(pathj):
            os.mkdir(pathj)
        if not os.path.exists(pathr):
            os.mkdir(pathr)
        
        for file in os.listdir(args.folder):
            root, extension = os.path.splitext(file)   
            
            if extension == ".png":
                png = args.folder + file
                dest = shutil.move(png, pathp)
            

            if extension == ".jpg":
                jpg = args.folder + file
                dest1 = shutil.move(jpg, pathj)
            





    elif args.command == "scan":
        print(f"Scanning {args.folder}...")
        
        for file in os.listdir(args.folder):
            root, extension = os.path.splitext(file)   
            
            if extension == ".jpg":
                print(f"Found image file {file}")
    else:
        parser.print_help()
