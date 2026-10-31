# Settings: default.toml holds every default, the user's config.toml is laid over the top of it
import difflib
import os
import tomllib
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace
from rich.errors import StyleSyntaxError
from rich.spinner import SPINNERS
from rich.style import Style
from cull.themes import THEMES

CHOICES = {
    "display.theme": list(THEMES),
    "display.color": ["auto", "always", "never"],
    "display.symbols": ["auto", "unicode", "ascii"],
    "display.table_box": ["rounded", "simple", "heavy", "double", "ascii", "minimal", "none"],
    "display.section_style": ["rule", "plain"],
    "display.score_order": ["name", "sharpness", "clipped"],
    "progress.style": ["bar", "spinner", "none"],
    "progress.spinner": list(SPINNERS),
    "folders.link": ["hardlink", "symlink", "copy"],
}

RANGES = {
    "display.decimals": (0, 6),
    "display.max_rows": (0, 1_000_000),
    "display.score_bar_width": (1, 100),
    "progress.bar_width": (1, 200),
    "progress.refresh_rate": (1, 60),
    "highlight.sharp_good": (0, 100),
    "highlight.sharp_poor": (0, 100),
    "highlight.clipped_warn": (0, 100),
    "highlight.clipped_bad": (0, 100),
    "scoring.long_edge": (32, 20_000),
    "scoring.blown": (1, 255),
    "scoring.crushed": (0, 254),
    "scoring.dark": (0, 255),
    "scoring.max_megapixels": (1, 10_000),
    "grouping.burst_gap": (0, 86_400),
    "grouping.scene_gap": (0, 86_400),
    "grouping.similar": (0, 64),
    "grouping.duplicate": (0, 64),
    "picks.clip_margin": (0, 100),
    "picks.same_sharpness": (0, 100),
    "folders.number_width": (1, 9),
    "review.port": (0, 65_535),
    "review.thumbnail": (64, 2048),
}

# These become part of a path, so "../photos" must not walk out of the shoot
NAMES = {"folders.singles_folder", "sort.rejects_folder"}
NAME_PARTS = {"folders.suffix", "folders.pick_prefix", "review.suffix"} # Added to a name, so these can't be a path either
EXTENSIONS = {"files.image_extensions", "files.raw_extensions", "sort.extensions"}


class ConfigError(Exception):
    pass


# $XDG_CONFIG_HOME is where Linux users expect to find it
def default_path():
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "cull" / "config.toml"


# An explicit path has to exist, the normal one is optional
def find_config(path=None):
    chosen = path or os.environ.get("CULL_CONFIG")
    return (Path(chosen).expanduser(), True) if chosen else (default_path(), False)


def default_text():
    return (files("cull") / "default.toml").read_text(encoding="utf-8")


def defaults():
    return tomllib.loads(default_text())


# Writes the commented defaults, this never replaces a config that's already there
def write_default(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as file:
        file.write(default_text())


def is_safe_name(value):
    return value not in ("", ".", "..") and not set(value) & {"/", "\\", ":", "\0"}


def fits_type(default, value):
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, float):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if isinstance(default, int):
        return isinstance(value, int) and not isinstance(value, bool)
    if isinstance(default, list):
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    return isinstance(value, str)


TYPE_NAMES = {bool: "true or false", int: "a whole number", float: "a number", str: "text in quotes", list: "a list of text"}


# Returns what's wrong with one value, or None if it's fine
def check_value(key, default, value):
    if not fits_type(default, value):
        return f"{key} must be {TYPE_NAMES[type(default)]}, not {value!r}"
    if key in CHOICES and value not in CHOICES[key]:
        return f"{key} can't be {value!r}, use: {', '.join(CHOICES[key])}"
    if key in RANGES:
        low, high = RANGES[key]
        if not low <= value <= high: # This also catches nan, TOML allows it
            return f"{key} must be between {low} and {high}, not {value!r}"
    if key in NAMES and not is_safe_name(value):
        return f"{key} must be a plain folder name, not {value!r}"
    if key in NAME_PARTS and value and not is_safe_name(value):
        return f"{key} can't contain a path, {value!r} isn't allowed"
    if key == "folders.suffix" and not value:
        return f"{key} can't be empty, the output folder would be the shoot itself"
    if key == "review.suffix" and not value:
        return f"{key} can't be empty, the decisions file would have the same name as the shoot"
    if key == "cache.folder" and not value:
        return f"{key} can't be empty"
    if key in EXTENSIONS:
        bad = [item for item in value if not is_safe_name(item.lstrip("."))]
        if bad:
            return f"{key} has an extension that can't be used: {bad[0]!r}"
    return None


# Style names are checked now, so a typo doesn't crash the first report
def check_color(name, value):
    if name not in THEMES["default"]:
        return f"colors.{name} isn't a color Cull uses{suggest(name, THEMES['default'])}"
    if not isinstance(value, str):
        return f"colors.{name} must be text in quotes, not {value!r}"
    try:
        Style.parse(value)
    except StyleSyntaxError:
        return f"colors.{name} can't be {value!r}, try a name like \"red\" or a hex color like \"#ff8800\""
    return None


def suggest(word, options):
    close = difflib.get_close_matches(word, options, n=1)
    return f", did you mean {close[0]}?" if close else ""


# Settings that can each be fine alone but make no sense together
def check_together(settings):
    problems = []
    if settings["scoring"]["crushed"] >= settings["scoring"]["blown"]:
        problems.append("scoring.crushed must be lower than scoring.blown")
    if settings["grouping"]["burst_gap"] > settings["grouping"]["scene_gap"]:
        problems.append("grouping.burst_gap can't be longer than grouping.scene_gap")
    if settings["highlight"]["sharp_poor"] > settings["highlight"]["sharp_good"]:
        problems.append("highlight.sharp_poor can't be higher than highlight.sharp_good")
    if settings["highlight"]["clipped_warn"] > settings["highlight"]["clipped_bad"]:
        problems.append("highlight.clipped_warn can't be higher than highlight.clipped_bad")
    return problems


# Lays the user's values over the defaults, a typo is a warning so the photos can still be scored
def merge(settings, user):
    problems, warnings = [], []

    for section, values in user.items():
        if section not in settings:
            warnings.append(f"Unknown section [{section}]{suggest(section, settings)}")
        elif not isinstance(values, dict):
            problems.append(f"{section} must be a [{section}] section")
        elif section == "colors":
            for name, value in values.items():
                problem = check_color(name, value)
                if problem:
                    problems.append(problem)
                else:
                    settings["colors"][name] = value
        else:
            for name, value in values.items():
                if name not in settings[section]:
                    warnings.append(f"Unknown setting {section}.{name}{suggest(name, settings[section])}")
                    continue
                problem = check_value(f"{section}.{name}", settings[section][name], value)
                if problem:
                    problems.append(problem)
                else:
                    settings[section][name] = value

    return problems + (check_together(settings) if not problems else []), warnings


# Extensions are compared lowercase, and the two lists differ on the leading dot
def normalize(settings):
    for key in ("image_extensions", "raw_extensions"):
        settings["files"][key] = {"." + item.lower().lstrip(".") for item in settings["files"][key]}
    settings["sort"]["extensions"] = [item.lower().lstrip(".") for item in settings["sort"]["extensions"]]


# Returns the settings as config.scoring.long_edge and so on
def load(path=None):
    settings = defaults()
    source, required = find_config(path)

    user = {}
    if required or source.exists():
        try:
            with open(source, "rb") as file:
                user = tomllib.load(file)
        except FileNotFoundError:
            raise ConfigError(f"No config file at {source}")
        except OSError as e:
            raise ConfigError(f"Couldn't read {source}: {e.strerror}")
        except ValueError as e: # Covers TOML mistakes and files that aren't text
            raise ConfigError(f"{source} isn't valid TOML: {e}")

    problems, warnings = merge(settings, user)
    if problems:
        raise ConfigError(f"Problems in {source}:\n" + "\n".join(f"  - {problem}" for problem in problems))

    normalize(settings)
    sections = {name: SimpleNamespace(**values) for name, values in settings.items() if name != "colors"}
    return SimpleNamespace(**sections, colors=settings["colors"], source=source, warnings=warnings, user=user)


# Everything that changes a stored score, so the cache can't return one made with other settings
def scoring_key(scoring):
    return f"{scoring.long_edge}:{scoring.blown}:{scoring.crushed}:{scoring.max_megapixels}"
