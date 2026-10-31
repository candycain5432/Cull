# Everything the terminal shows: colors, tables, progress bars. Reports go to stdout and progress to stderr
import time
from contextlib import contextmanager
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (BarColumn, MofNCompleteColumn, Progress, ProgressColumn, SpinnerColumn,
                           TaskProgressColumn, TextColumn, TimeRemainingColumn)
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from cull.themes import THEMES

BOXES = {"rounded": box.ROUNDED, "simple": box.SIMPLE, "heavy": box.HEAVY, "double": box.DOUBLE,
         "ascii": box.ASCII, "minimal": box.MINIMAL, "none": None}

SYMBOLS = {
    "unicode": {"pick": "★", "dot": "·", "full": "█", "empty": "░", "warn": "⚠", "done": "✔", "more": "…"},
    "ascii": {"pick": "*", "dot": "-", "full": "#", "empty": ".", "warn": "!", "done": "+", "more": "..."},
}

UNLIMITED = 1_000_000 # Columns when printing plain text, so a long name doesn't get cut
SMALLEST = 60 # Columns, a table narrower than this can't fit a score and a file name
FULL_TABLE = 100 # Columns, narrower than this a report leaves out its less important scores
BARS = 80 # Columns, narrower than this a report leaves out its score bars
BIG_TABLE = 2000 # Rows, a framed table this long takes over a second to draw


# Photos per second, the rate is unknown until a couple of photos are done
class SpeedColumn(ProgressColumn):
    def render(self, task):
        return Text(f"{task.speed:.1f}/s" if task.speed else "", style="muted")


# Keeps the end of a long name, that's the part that tells two photos apart
def shorten(name, width=28, more="…"):
    return name if len(name) <= width else more + name[len(more) - width:]


def make_console(display, theme, stderr=False):
    options = {"theme": theme, "stderr": stderr, "markup": False, "emoji": False, "highlight": False}
    if display.color == "never":
        options["color_system"] = None
    if display.color == "always" and not stderr:
        options["force_terminal"] = True

    return Console(**options)


class Ui:
    def __init__(self, config):
        self.config = config
        self.display = config.display
        self.started = time.perf_counter()

        colors = THEMES[self.display.theme] | config.colors
        theme = Theme(colors, inherit=True)
        self.out = make_console(self.display, theme)
        self.err = make_console(self.display, theme, stderr=True)

        # Output going to a file or a pipe stays as plain columns, so it can be searched and sorted
        self.fancy = self.out.is_terminal and self.out.width >= SMALLEST
        if not self.fancy:
            self.out.width = UNLIMITED
        text_ok = (self.out.encoding or "").lower().startswith("utf")
        self.symbols = SYMBOLS["ascii" if self.display.symbols == "ascii" or
                               (self.display.symbols == "auto" and not text_ok) else "unicode"]

    def line(self, text="", style=None):
        self.out.print(Text(text, style=style or ""), soft_wrap=True)

    def warn(self, text):
        self.err.print(Text(f"{self.symbols['warn']} {text}", style="warn"), soft_wrap=True)

    def title(self, action, folder):
        if self.fancy and self.display.banner:
            self.out.print(Text.assemble(("Cull", "accent"), f" {self.symbols['dot']} {action} ", (str(folder), "muted")),
                           soft_wrap=True)
        else:
            self.line(f"{action} {folder}...")

    def section(self, text, style="heading"):
        if self.fancy and self.display.section_style == "rule":
            self.out.print()
            self.out.print(Rule(Text(f" {text} ", style=style), align="left", style="muted"))
        else:
            self.line()
            self.line(f" === {text} ===", style)

    # A left column is text and wraps on a narrow terminal, the others never wrap
    def table(self, *columns, framed=True, header=True):
        table = Table(box=BOXES[self.display.table_box] if self.fancy and framed else None, show_header=header,
                      header_style="heading", border_style="muted", pad_edge=self.fancy and framed,
                      row_styles=["", "stripe"] if self.fancy and self.display.stripes else None)
        for title, justify in columns:
            table.add_column(title, justify=justify, no_wrap=justify != "left", overflow="fold")
        return table

    def show(self, table):
        if self.fancy and table.row_count < BIG_TABLE:
            self.out.print(table)
        else:
            self.print_columns(table)

    # Plain columns built as one piece of text, Rich draws each cell of a table on its own
    def print_columns(self, table):
        columns = []
        for column in table.columns:
            cells = [cell if isinstance(cell, Text) else Text(cell) for cell in column.cells]
            columns.append([Text(column.header, style="heading")] * table.show_header + cells)
        widths = [max(cell.cell_len for cell in cells) for cells in columns]

        rows = []
        for row in zip(*columns):
            parts = []
            for cell, width, column in zip(row, widths, table.columns):
                gap = " " * (width - cell.cell_len)
                parts.append(Text.assemble(cell, gap) if column.justify == "left" else
                             Text.assemble(gap[:len(gap) // 2], cell, gap[len(gap) // 2:]) if column.justify == "center" else
                             Text.assemble(gap, cell))
            rows.append(Text("  ").join(parts))
            rows[-1].rstrip()
        if rows:
            self.out.print(Text("\n").join(rows), soft_wrap=True)

    # Text for a table cell, a file name is never read as formatting this way
    def cell(self, text, style=""):
        return Text(str(text), style=style)

    # One line of the scan report
    def field(self, tag, value):
        self.out.print(Text.assemble((f"{tag!s:25}", "muted"), f": {value}"), soft_wrap=True)

    def pick_label(self):
        return f"{self.symbols['pick']} PICK" if self.fancy else "PICK"

    def number(self, value):
        return f"{value:.{self.display.decimals}f}"

    def percent(self, value):
        return f"{self.number(value)}%"

    # A bar filled to a fraction between 0 and 1
    def meter(self, fraction, style):
        width = self.display.score_bar_width
        filled = round(max(0, min(1, fraction)) * width)
        return Text.assemble((self.symbols["full"] * filled, style), (self.symbols["empty"] * (width - filled), "muted"))

    @property
    def bars(self):
        return self.fancy and self.display.score_bars and self.out.width >= BARS

    @property
    def compact(self):
        return self.fancy and self.out.width < FULL_TABLE

    # Says which columns a narrow terminal is missing, so they don't look like they're gone
    def left_out(self, names):
        if self.compact:
            self.line(f"{names} left out, a terminal {FULL_TABLE} columns wide shows them", "muted")

    def sharp_style(self, beats):
        marks = self.config.highlight
        return "good" if beats >= marks.sharp_good else "bad" if beats < marks.sharp_poor else "warn"

    def clip_style(self, clipped):
        marks = self.config.highlight
        return "bad" if clipped >= marks.clipped_bad else "warn" if clipped >= marks.clipped_warn else "good"

    # The rows a report should show, and how many were left out
    def limit(self, rows):
        most = self.display.max_rows
        return (rows[:most], len(rows) - most) if most and len(rows) > most else (rows, 0)

    def hidden(self, count):
        if count:
            self.line(f"{self.symbols['more']} and {count} more, change max_rows in the config to see them", "muted")

    def summary(self, parts, note=None):
        if not self.display.summary:
            if note:
                self.line(note)
            return
        if self.display.elapsed:
            parts = parts + [f"{time.perf_counter() - self.started:.1f}s"]

        if self.fancy:
            text = Text(f" {self.symbols['dot']} ".join(parts), style="heading")
            if note:
                text.append(f"\n{note}", style="muted")
            self.out.print()
            self.out.print(Panel.fit(text, border_style="muted", box=BOXES[self.display.table_box] or box.SIMPLE))
        else:
            self.line()
            self.line(", ".join(parts))
            if note:
                self.line(note)

    def can_animate(self):
        return self.config.progress.style != "none" and self.err.is_interactive

    # A spinner for steps with no count, like walking a big folder
    @contextmanager
    def working(self, label):
        if not self.can_animate():
            yield
            return
        with self.err.status(Text(label, style="muted"), spinner=self.config.progress.spinner, spinner_style="accent"):
            yield

    # Yields a function to call after each item with the item's name
    @contextmanager
    def progress(self, label, total):
        if not self.can_animate() or not total:
            yield lambda name: None
            return

        settings = self.config.progress
        columns = [SpinnerColumn(settings.spinner, style="accent", finished_text=self.symbols["done"]),
                   TextColumn("{task.description}", markup=False)]
        if settings.style == "bar":
            columns.append(BarColumn(settings.bar_width, style="muted", complete_style="bar", finished_style="bar_done"))
        if settings.percent:
            columns.append(TaskProgressColumn(text_format="{task.percentage:>3.0f}%", markup=False))
        if settings.count:
            columns.append(MofNCompleteColumn())
        if settings.speed:
            columns.append(SpeedColumn())
        if settings.eta:
            columns.append(TimeRemainingColumn())
        if settings.current_file:
            columns.append(TextColumn("{task.fields[file]}", markup=False, style="muted"))

        with Progress(*columns, console=self.err, transient=not settings.keep_finished,
                      refresh_per_second=settings.refresh_rate) as bar:
            task = bar.add_task(label, total=total, file="")
            yield lambda name: bar.update(task, advance=1, file=shorten(name, more=self.symbols["more"]))
