import re
import sys
import time
from collections.abc import Sequence
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from rich import box
from rich.table import Table
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Footer, Static

from timetracker.models import Task
from timetracker.parsers import to_aware_string

DAYS_IN_SECONDS = 60 * 60 * 24
YEARS_IN_SECONDS = DAYS_IN_SECONDS * 365.25
NUMBERS = [
    "████████\n██    ██\n██    ██\n██    ██\n██    ██\n██    ██\n████████",
    "      ██\n      ██\n      ██\n      ██\n      ██\n      ██\n      ██",
    "████████\n      ██\n      ██\n████████\n██      \n██      \n████████",
    "████████\n      ██\n      ██\n████████\n      ██\n      ██\n████████",
    "██    ██\n██    ██\n██    ██\n████████\n      ██\n      ██\n      ██",
    "████████\n██      \n██      \n████████\n      ██\n      ██\n████████",
    "████████\n██      \n██      \n████████\n██    ██\n██    ██\n████████",
    "████████\n      ██\n      ██\n      ██\n      ██\n      ██\n      ██",
    "████████\n██    ██\n██    ██\n████████\n██    ██\n██    ██\n████████",
    "████████\n██    ██\n██    ██\n████████\n      ██\n      ██\n████████",
]
COLON = "    \n████\n████\n    \n████\n████\n    "


def get_time_as_ascii_string(duration: str) -> str:
    pattern = re.compile(r".*(?P<time>\d{2}:\d{2}:\d{2})")
    match = pattern.fullmatch(duration)
    if match is None:
        raise ValueError
    time_str = match.group("time")
    ascii_chars = []
    for time_char in time_str:
        if time_char.isdecimal():
            ascii_chars.append(NUMBERS[int(time_char)])
        else:
            ascii_chars.append(COLON)
    ascii_chars = [char.split("\n") for char in ascii_chars]
    result = ""
    for i in range(0, 7):
        for char in ascii_chars:
            result += char[i] + "    "
        result = result[:-4]
        result += "\n"
    return result


def format_seconds(total_seconds: float) -> str:
    years, remainder = divmod(total_seconds, YEARS_IN_SECONDS)
    years = int(years)
    remainder = int(remainder)
    days, remainder = divmod(remainder, DAYS_IN_SECONDS)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    result = ""
    if years != 0:
        if years == 1:
            result += "1 year, "
        else:
            result += f"{years} years, "
    if days != 0:
        if days == 1:
            result += "1 day, "
        else:
            result += f"{days} days, "
    result += f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return result


def display_updating_time(start: datetime, task: str, project: str) -> None:
    print("Press CTRL+C to exit!")
    print(f"{project} > {task}")
    while True:
        try:
            delta = datetime.utcnow() - start
            time_str = format_seconds(delta.total_seconds())
            print(time_str, end="\r")
            time.sleep(0.25)
        except KeyboardInterrupt:
            print(time_str)
            sys.exit()


class StatusDisplay(App):
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    class Clock(Static):
        time_str = reactive("00:00:00")

        def __init__(self, start: datetime, task: str, project: str) -> None:
            super().__init__("")
            self.start = start
            self.task_ = task
            self.project = project

        def on_mount(self) -> None:
            self.set_interval(0.25, self.update_time_str)
            self.styles.height = "100%"
            self.styles.content_align = ("center", "middle")
            self.styles.border = ("heavy", "white")
            self.styles.border_title_style = "bold"
            self.border_title = f"{self.project} > {self.task_}"
            self.border_subtitle = "press q to quit"

        def update_time_str(self) -> None:
            delta = datetime.utcnow() - self.start
            self.time_str = format_seconds(delta.total_seconds())

        def watch_time_str(self, time_str: str) -> None:
            self.update(get_time_as_ascii_string(time_str))

    def __init__(self, start: datetime, task: str, project: str) -> None:
        super().__init__()
        self.start = start
        self.task_ = task
        self.project = project

    def compose(self) -> ComposeResult:
        clock = self.Clock(self.start, self.task_, self.project)
        yield clock

    def on_mount(self) -> None:
        pass


class RecapDisplay(App):
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    def __init__(self, tasks: Sequence[Task], tz: ZoneInfo, sections: str, show_id: bool) -> None:
        super().__init__()
        self.tasks = tasks
        self.tz = tz
        self.sections = sections
        self.show_id = show_id

    def compose(self) -> ComposeResult:
        table = Table(expand=True, row_styles=["white on grey19", "white"], box=box.ROUNDED)

        if self.show_id:
            table.add_column("ID")
        table.add_column("Project")
        table.add_column("Task")
        table.add_column("Note")
        table.add_column("Start")
        table.add_column("End")
        table.add_column("Duration")

        previous_task_start = self.tasks[0].start
        for task in self.tasks:
            if self.new_section_started(previous_task_start, task.start):
                table.add_section()
            previous_task_start = task.start

            delta = task.end - task.start
            duration = format_seconds(delta.total_seconds())

            args = [
                task.project.name,
                task.name,
                task.note,
                to_aware_string(task.start, self.tz),
                to_aware_string(task.end, self.tz),
                duration,
            ]
            if self.show_id:
                args.insert(0, str(task.id))
            table.add_row(*args)

        yield Static(table)
        yield Footer()

    def new_section_started(self, previous_dt: datetime, next_dt: datetime) -> bool:
        if self.sections == "none":
            return False
        elif self.sections == "days":
            return (
                previous_dt.day != next_dt.day
                or previous_dt.month != next_dt.month
                or previous_dt.year != next_dt.year
            )
        elif self.sections == "weeks":
            week_end = previous_dt + timedelta(days=6-previous_dt.weekday())
            week_end = week_end.replace(hour=23, minute=59, second=59, microsecond=999999)
            return next > week_end
        elif self.sections == "months":
            return previous_dt.month != next_dt.month or previous_dt.year != next_dt.year
        else:
            raise ValueError
