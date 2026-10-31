# Importing Modules
import argparse
import json
import os
import shutil
from collections import Counter
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS, IFD
from importlib.metadata import version
import io
import sys
import rawpy
from bisect import bisect_left
from rich.text import Text
from cull.analyze import UNREADABLE, analyze_folder, find_files, set_pixel_limit
from cull.config import ConfigError, defaults, find_config, load, write_default
from cull.folders import output_folder, write_folders
from cull.grouping import group_photos
from cull.picks import choose
from cull.themes import THEMES
from cull.ui import Ui

# Scores every photo, then lists the ones that couldn't be opened
def read_photos(folder, config, ui):
    photos, skipped, ignored, fresh = analyze_folder(Path(folder), config, ui)
    if config.display.show_unreadable:
        for name, error in skipped:
            ui.line(f"Skipping {name}: {error}", "warn")
    if not photos and not skipped:
        ui.warn(f"No photos found in {folder}")
    return photos, len(skipped), ignored, fresh

# The totals at the end of every report
def print_summary(ui, photos, skipped_bad, skipped_ext, fresh, first=(), note=None):
    ui.summary([*first, f"{len(photos)} scored", f"{skipped_bad} unreadable", f"{skipped_ext} ignored by extension",
                f"{fresh} newly analyzed"], note)

# Sharpness is relative, so it's shown as the % of this shoot a photo beats
def beats(comparable, photo):
    return bisect_left(comparable, photo.sharpness) / max(1, len(comparable) - 1) * 100

# Shows how Cull is set up right now
def show_config(config, ui):
    source = f"from {config.source}" if config.source.exists() else f"are the defaults, there's no file at {config.source}"
    ui.line(f"Settings {source}", "muted")

    for section, values in defaults().items():
        if section == "colors":
            continue
        ui.section(f"[{section}]")
        table = ui.table(("", "left"), ("", "left"), ("", "left"), framed=False, header=False)
        for name, default in values.items():
            value = config.user.get(section, {}).get(name, default)
            changed = value != default
            table.add_row(ui.cell(name), ui.cell(json.dumps(value), "accent" if changed else ""),
                          ui.cell(f"default {json.dumps(default)}" if changed else "", "muted"))
        ui.show(table)

    ui.section("[colors]")
    table = ui.table(("", "left"), ("", "left"), framed=False, header=False)
    for name, style in (THEMES[config.display.theme] | config.colors).items():
        table.add_row(ui.cell(name), ui.cell(style, name))
    ui.show(table)

    for warning in config.warnings:
        ui.warn(warning)

# A sample of every theme, so one can be chosen without trying them all
def show_themes(config, ui):
    table = ui.table(("theme", "left"), ("sample", "left"))
    for name, colors in THEMES.items():
        current = " (in use)" if name == config.display.theme else ""
        sample = Text.assemble((f"{ui.symbols['pick']} PICK", colors["pick"]), "  ", ("sharp", colors["good"]), "  ",
                                      ("check", colors["warn"]), "  ", ("blurry", colors["bad"]), "  ",
                                      ("quiet", colors["muted"]), "  ", (ui.symbols["full"] * 6, colors["bar"]),
                                      (ui.symbols["full"] * 3, colors["bar_done"]))
        table.add_row(ui.cell(name + current), sample)
    ui.show(table)

# Entry point, stopping a long scan is normal so it shouldn't print a traceback
def main():
    try:
        run()
    except KeyboardInterrupt:
        print("\nStopped, photos analyzed so far are saved in the cache")
        sys.exit(130)

# Main function
def run():
    sys.stdout.reconfigure(errors="replace") # So an odd file name can't crash a report

    # Flags that work on every command, SUPPRESS stops a subcommand's default wiping out the main parser's value
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=argparse.SUPPRESS, metavar="FILE", help="Use this config file")
    common.add_argument("--no-color", action="store_true", default=argparse.SUPPRESS, help="Turn colors off")
    common.add_argument("--no-progress", action="store_true", default=argparse.SUPPRESS, help="Hide progress bars")

    # Adds the commands like --help and sort etc
    parser = argparse.ArgumentParser(prog="cull", description="Photo culling assistant", parents=[common],
                                     epilog="Colors, thresholds and folder names can be changed, run: cull config init")
    parser.add_argument("--version", action="version", version=f"cull {version('cull')}")
    sub = parser.add_subparsers(dest="command")
    
    scan = sub.add_parser("scan", parents=[common], help="Print the EXIF data of every photo") # Adds <scan> command 
    sorter = sub.add_parser("sort", parents=[common], help="sort the photos into folders based on file extension") # Adds <sort> command
    sharp = sub.add_parser("sharpness", parents=[common], help="Rank photos from sharpest to blurriest") # Adds <sharpness> command
    expose = sub.add_parser("exposure", parents=[common], help="Rank photos from best to worst exposed") # Adds <exposure> command
    score = sub.add_parser("score", parents=[common], help="Show every score for every photo") # Adds <score> command
    grouper = sub.add_parser("group", parents=[common], help="Group similar shots and suggest the best of each") # Adds <group> command
    configure = sub.add_parser("config", parents=[common], help="Show or create the config file") # Adds <config> command
    sorter.add_argument("folder", help="path to the shoot")
    scan.add_argument("folder", help="Path to the shoot")
    sharp.add_argument("folder", help="Path to the shoot")
    expose.add_argument("folder", help="Path to the shoot")
    score.add_argument("folder", help="Path to the shoot")
    grouper.add_argument("folder", help="Path to the shoot")
    configure.add_argument("action", nargs="?", default="show", choices=["show", "init", "path", "themes"],
                           help="show the settings, init a config file, print its path, or preview the themes")

    args = parser.parse_args()
    config_file = getattr(args, "config", None)

    # A typo in the path should be an error, <sort> would create the folder otherwise
    if args.command not in (None, "config") and not os.path.isdir(args.folder):
        parser.error(f"{args.folder} is not a folder")

    # These two have to work when the config is broken, that's when they're needed
    if args.command == "config" and args.action == "path":
        path, _ = find_config(config_file)
        print(path if path.exists() else f"{path} (doesn't exist yet, create it with: cull config init)")
        return

    if args.command == "config" and args.action == "init":
        path, _ = find_config(config_file)
        try:
            write_default(path)
            print(f"Created {path}")
        except FileExistsError:
            print(f"{path} already exists, delete it to start again")
        except OSError as e:
            parser.exit(2, f"cull: Couldn't write {path}: {e.strerror}\n")
        return

    try:
        config = load(config_file)
    except ConfigError as e:
        parser.exit(2, f"cull: {e}\n")

    if getattr(args, "no_color", False):
        config.display.color = "never"
    if getattr(args, "no_progress", False):
        config.progress.style = "none"

    ui = Ui(config)
    set_pixel_limit(config.scoring.max_megapixels)

    if args.command != "config": # <config> lists these after the settings
        for warning in config.warnings:
            ui.warn(f"{warning} ({config.source})")
    
    

# Don't you guys love coding? you won't once you read the code below


    # Sorts all the files in the folder
    if args.command == "sort":
        ui.title("Sorting", args.folder)
        
        extensions = config.sort.extensions # List for allowed file types
        pathreject = os.path.join(args.folder, config.sort.rejects_folder)
        
        # Creates folder inside target folder for each file type in list, and a "Rejects" folder for the rest
        if config.sort.keep_empty_folders:
            for ext in extensions:
                os.makedirs(os.path.join(args.folder, ext), exist_ok=True) # Error avoidence
            os.makedirs(pathreject, exist_ok=True)

        # looks at every file
        files = [file for file in os.listdir(args.folder) if os.path.isfile(os.path.join(args.folder, file))]
        moved = Counter()
        skipped = []

        with ui.progress("Sorting", len(files)) as step:
            for file in files:
                src = os.path.join(args.folder, file) # Full path of current entry
                
                # Split the filename
                root, extension = os.path.splitext(file)
                ext = extension.lower().lstrip(".") # Fixes cace sensitivity
            
                # Choses the destination
                if ext in extensions:
                    dest = os.path.join(args.folder, ext)
                else:
                    dest = pathreject
                os.makedirs(dest, exist_ok=True)
                
                # Move the file, this refuses to overwrite one that's already there
                try:
                    shutil.move(src, dest)
                    moved[os.path.basename(dest)] += 1
                except shutil.Error as e:
                    skipped.append(f"Skipping {file}: {e}")
                step(file)

        for message in skipped:
            ui.line(message, "warn")

        if moved:
            table = ui.table(("folder", "left"), ("files", "right"))
            for name, count in sorted(moved.items()):
                table.add_row(ui.cell(name), str(count))
            ui.show(table)
        
        ui.summary([f"{sum(moved.values())} moved", f"{len(skipped)} skipped"])


    

    # Scans folders and prints EXIF data
    elif args.command == "scan":
        def read_exif(file):
            if file.suffix.lower() in config.files.raw_extensions:
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
            if config.scan.show_gps:
                for tag_id, value in exif.get_ifd(IFD.GPSInfo).items():
                    out[GPSTAGS.get(tag_id, tag_id)] = value
            return out



        ui.title("Scanning", args.folder)
        folder = Path(args.folder) # Turns string into path       
        
        # Counters for the summary at the end
        scanned = skipped_ext = skipped_bad = 0

        with ui.working("Finding photos"):
            files = find_files(folder, config.files) # Recursive Scan
        
        for file in files:
            # Skips anything that is not a image (from list)
            if file.suffix.lower() not in config.files.image_extensions | config.files.raw_extensions:
                skipped_ext += 1
                continue
            
            # Prints file name in a green header
            ui.section(file.name, "good")

            try:

                exifdata = read_exif(file)
                for tag, data in exifdata.items():
                    if tag in config.scan.hide_tags:
                        continue
                    if isinstance(data, bytes):
                        try:
                            text = data.decode("utf-8")
                        except UnicodeDecodeError:
                            text = None
                        data = text if text and text.isprintable() else f"<{len(data)} bytes>"



                    ui.field(tag, data)

                scanned += 1
            
            # Corrupt, empty or fake image files end up here
            except UNREADABLE as e:
                ui.line(f"Skipping {file.name}: {e}", "warn")
                skipped_bad += 1
        
        # Summary
        ui.summary([f"{scanned} scanned", f"{skipped_bad} unreadable", f"{skipped_ext} ignored by extension"])



    # Ranks photos from sharpest to blurriest
    elif args.command == "sharpness":
        ui.title("Scoring", args.folder)
        photos, skipped_bad, skipped_ext, fresh = read_photos(args.folder, config, ui)

        long_edge = config.scoring.long_edge
        ranked = [photo for photo in photos if photo.long_edge >= long_edge]
        too_small = [photo for photo in photos if photo.long_edge < long_edge]
        comparable = sorted(photo.sharpness for photo in ranked)

        columns = [("#", "right"), ("sharpness", "right"), ("beats", "right"), ("photo", "left")]
        if ui.bars:
            columns.insert(3, ("", "center"))

        def add_row(table, label, photo, percent):
            style = ui.sharp_style(percent)
            row = [label, ui.cell(ui.number(photo.sharpness), style), f"{percent:.0f}%"]
            if ui.bars:
                row.append(ui.meter(percent / 100, style))
            table.add_row(*row, ui.cell(photo.name))

        ui.section("Sharpest to blurriest", "good")
        rows, hidden = ui.limit(sorted(ranked, key=lambda photo: photo.sharpness, reverse=True))
        table = ui.table(*columns)
        for rank, photo in enumerate(rows, 1):
            add_row(table, f"{rank}", photo, beats(comparable, photo))
        ui.show(table)
        ui.hidden(hidden)

        # Small images score too high, so they can't be compared with the ranking above
        if too_small:
            ui.section(f"Under {long_edge}px, not comparable with the ranking above", "warn")
            table = ui.table(("sharpness", "right"), ("photo", "left"))
            for photo in sorted(too_small, key=lambda photo: photo.sharpness, reverse=True):
                table.add_row(ui.number(photo.sharpness), ui.cell(photo.name))
            ui.show(table)

        print_summary(ui, photos, skipped_bad, skipped_ext, fresh)



    # Ranks photos from best to worst exposed
    elif args.command == "exposure":
        ui.title("Scoring", args.folder)
        photos, skipped_bad, skipped_ext, fresh = read_photos(args.folder, config, ui)

        dark_below = config.scoring.dark
        ranked = [photo for photo in photos if photo.brightness >= dark_below]
        dark = [photo for photo in photos if photo.brightness < dark_below]

        columns = [("#", "right"), ("clipped", "right")]
        if not ui.compact:
            columns += [("blown", "right"), ("crushed", "right")]
        columns.append(("bright", "right"))
        if ui.bars:
            columns.append(("", "center"))
        columns.append(("photo", "left"))

        # The bar is full at twice the clipping that turns a score red
        def add_row(table, label, photo):
            style = ui.clip_style(photo.clipped)
            row = [label, ui.cell(ui.percent(photo.clipped), style)]
            if not ui.compact:
                row += [ui.percent(photo.blown), ui.percent(photo.crushed)]
            row.append(f"{photo.brightness:.0f}")
            if ui.bars:
                row.append(ui.meter(photo.clipped / (config.highlight.clipped_bad * 2 or 1), style))
            table.add_row(*row, ui.cell(photo.name))

        ui.section("Best to worst exposed", "good")
        rows, hidden = ui.limit(sorted(ranked, key=lambda photo: (photo.clipped, photo.name)))
        table = ui.table(*columns)
        for rank, photo in enumerate(rows, 1):
            add_row(table, f"{rank}", photo)
        ui.show(table)
        ui.hidden(hidden)

        # Underexposed photos and real night scenes look the same, so these aren't ranked
        if dark:
            ui.section("Very dark, could be underexposed or a night scene, check by eye", "warn")
            table = ui.table(*columns)
            for photo in sorted(dark, key=lambda photo: photo.brightness):
                add_row(table, "", photo)
            ui.show(table)

        ui.left_out("Blown and crushed are")
        print_summary(ui, photos, skipped_bad, skipped_ext, fresh)



    # Shows every category side by side
    elif args.command == "score":
        ui.title("Scoring", args.folder)
        photos, skipped_bad, skipped_ext, fresh = read_photos(args.folder, config, ui)

        long_edge = config.scoring.long_edge
        comparable = sorted(photo.sharpness for photo in photos if photo.long_edge >= long_edge)
        orders = {"name": lambda photo: photo.name, "sharpness": lambda photo: -photo.sharpness, "clipped": lambda photo: photo.clipped}

        ui.section("Scores", "good")
        columns = [("sharp", "right"), ("beats", "right"), ("clipped", "right")]
        if not ui.compact:
            columns += [("blown", "right"), ("crushed", "right"), ("bright", "right")]
        table = ui.table(*columns, ("note", "center"), ("photo", "left"))
        rows, hidden = ui.limit(sorted(photos, key=orders[config.display.score_order]))
        for photo in rows:
            small = photo.long_edge < long_edge
            percent = beats(comparable, photo)
            note = "small" if small else "dark" if photo.brightness < config.scoring.dark else ""
            row = [ui.cell(ui.number(photo.sharpness), "muted" if small else ui.sharp_style(percent)),
                   "-" if small else f"{percent:.0f}%",
                   ui.cell(ui.percent(photo.clipped), ui.clip_style(photo.clipped))]
            if not ui.compact:
                row += [ui.percent(photo.blown), ui.percent(photo.crushed), f"{photo.brightness:.0f}"]
            table.add_row(*row, ui.cell(note, "warn"), ui.cell(photo.name))
        ui.show(table)
        ui.hidden(hidden)

        ui.left_out("Blown, crushed and brightness are")
        print_summary(ui, photos, skipped_bad, skipped_ext, fresh)



    # Groups similar shots and suggests the best of each
    elif args.command == "group":
        ui.title("Grouping", args.folder)
        photos, skipped_bad, skipped_ext, fresh = read_photos(args.folder, config, ui)
        with ui.working("Grouping photos"):
            groups, singles = group_photos(photos, config.grouping)
        decided = []

        columns = [("", "right"), ("", "left")]
        if config.display.show_reasons:
            columns.append(("", "left"))

        for group in groups:
            pick, reasons = choose(group, config.picks, config.scoring.long_edge)
            decided.append((group, pick))

            ui.section(f"{group.kind}, {len(group.photos)} photos", "good")
            table = ui.table(*columns, framed=False, header=False)
            table.add_row(ui.cell(ui.pick_label(), "pick"), ui.cell(pick.name, "pick"), ui.cell(reasons[pick.name]))
            for photo in group.photos:
                if photo is not pick:
                    table.add_row("", ui.cell(photo.name), ui.cell(reasons[photo.name], "muted"))
            ui.show(table)

        # Nothing to compare these with, so there's no decision to make
        if singles and config.display.show_singles:
            ui.section(f"No similar shots, {len(singles)} photos", "warn")
            for photo in sorted(singles, key=lambda photo: photo.name):
                ui.line(f"      {photo.name}")

        # Never overwrites old folders, the photographer may have sorted through them
        output = output_folder(Path(args.folder), config.folders)
        note = None
        if config.folders.write and photos:
            if output.exists():
                note = f"{output} already exists, delete it to rebuild the folders"
            else:
                total = sum(len(group.photos) for group in groups) + (len(singles) if config.folders.write_singles else 0)
                try:
                    with ui.progress("Writing folders", total) as step:
                        write_folders(Path(args.folder), decided, singles, config.folders, step)
                    note = f"Folders written to {output}"
                except OSError as e:
                    ui.warn(f"Couldn't write the folders: {e}")

        print_summary(ui, photos, skipped_bad, skipped_ext, fresh, [f"{len(groups)} groups", f"{len(singles)} singles"], note)



    # Shows the settings in use, or a preview of the themes
    elif args.command == "config":
        if args.action == "themes":
            show_themes(config, ui)
        else:
            show_config(config, ui)



    else:
        parser.print_help()
