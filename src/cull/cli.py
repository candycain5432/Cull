import argparse

def main():

    parser = argparse.ArgumentParser(prog="cull", description="Photo culling assistant",)
    sub = parser.add_subparsers(dest="command")
    
    scan = sub.add_parser("scan", help="Analyze a folder of photos")
    scan.add_argument("folder", help="Path to the shoot")

    args = parser.parse_args()

    if args.command == "scan":
        print(f"Scanning {args.folder}...")
    else:
        parser.print_help()
