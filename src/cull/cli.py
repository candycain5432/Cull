# Importing Modules
import argparse
import os
import shutil

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
        
        extensions = ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp", "avif", "heic"] # List for allowed file types (There will be a option to add to this in the cli)
        
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
            if ext in extension:
                dest = os.path.join(args.folder, ext)
            else:
                dest = pathreject
            
            # Move the file
            shutil.move(src, dest)


    

    # Scans folders (Doesn't do anything yet)
    elif args.command == "scan":
        print(f"Scanning {args.folder}...")
        
        for file in os.listdir(args.folder):
            root, extension = os.path.splitext(file)   
            
            if extension == ".jpg":
                print(f"Found image file {file}")
    else:
        parser.print_help()
