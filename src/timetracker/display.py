import sys
from collections.abc import Sequence
from datetime import datetime, timedelta
from time import sleep
from zoneinfo import ZoneInfo

from rich import box
from rich.live import Live
from rich.table import Table
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Footer, Static

from .models import Task
from .settings import Settings
from .time_utils import format_seconds, get_time_as_ascii_string, to_aware_string


def display_status(type_: str, task: Task, tz: ZoneInfo) -> None:
    match type_:
        case ("basic" | "b"):
            display_updating_time(task)
        case ("table" | "t"):
            display_status_table(task, tz)
        case ("fullscreen" | "f"):
            app = StatusDisplay(task)
            app.run()
        case _:
            raise ValueError


def display_updating_time(task: Task) -> None:
    print("Press CTRL+C to exit!")
    print(f"{task.project.name} > {task.name}")
    # this is to avoid rounding errors
    start = task.start.replace(microsecond=0)
    target = None if task.target is None else task.target.replace(microsecond=0)
    while True:
        try:
            if target is None:
                message = get_status_message_without_target(start)
            else:
                message = get_status_message_with_target(start, target)
            print(message, end="\r")
            sleep(0.25)
        except KeyboardInterrupt:
            print(message)
            sys.exit(0)


def get_status_message_without_target(start: datetime) -> str:
    delta = datetime.utcnow() - start
    string = format_seconds(delta.total_seconds())
    return f"The task has been running for {string}"


def get_status_message_with_target(start: datetime, target: datetime) -> str:
    now = datetime.utcnow().replace(microsecond=0)
    start_delta = now - start
    start_string = format_seconds(start_delta.total_seconds())
    target_delta = target - now
    target_string = format_seconds(target_delta.total_seconds())

    message = f"The task has been running for {start_string} and the target "
    if target_delta.total_seconds() > 0:
        message += f"is reached in {target_string}"
    else:
        message += f"has been reached {target_string} ago"

    return message


def display_status_table(task: Task, tz: ZoneInfo) -> None:

    def generate_status_table() -> Table:
        now = datetime.utcnow()
        start_delta = now - task.start
        run_time = format_seconds(start_delta.total_seconds())

        table = Table(show_header=False, show_lines=True, box=box.ROUNDED)
        table.add_row("Task", task.project.name)
        table.add_row("Project", task.name)
        table.add_row("Start", to_aware_string(task.start, tz, "%d/%m/%Y %H:%M:%S"))
        table.add_row("Run Time", run_time)

        if task.target is not None:
            table.add_row("Target", to_aware_string(task.target, tz, "%d/%m/%Y %H:%M:%S"))

            target_delta = task.target - now
            target_string = format_seconds(target_delta.total_seconds())
            if target_delta.total_seconds() > 0:
                table.add_row("Countdown", target_string)
            else:
                table.add_row("Overtime", target_string)

        return table

    print("Press CTRL+C to exit!")
    with Live(get_renderable=generate_status_table, refresh_per_second=4):
        while True:
            try:
                sleep(0.2)
            except KeyboardInterrupt:
                print(generate_status_table())
                sys.exit(0)


class StatusDisplay(App):
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    class Clock(Static):
        time_str = reactive("00:00:00")

        def __init__(self, task: Task) -> None:
            super().__init__("")
            self.task_ = task

        def on_mount(self) -> None:
            if self.task_.target is not None:
                self.set_interval(0.25, self.update_target)
            else:
                self.set_interval(0.25, self.update_run_time)
            self.styles.height = "100%"
            self.styles.content_align = ("center", "middle")
            self.styles.border = ("heavy", "white")
            self.styles.border_title_style = "bold"
            self.border_title = f"{self.task_.project.name} > {self.task_.name}"
            self.border_subtitle = "press q to quit"

        def update_run_time(self) -> None:
            delta = datetime.utcnow() - self.task_.start
            self.time_str = format_seconds(delta.total_seconds())

        def update_target(self) -> None:
            delta = self.task_.target - datetime.utcnow()
            self.time_str = format_seconds(delta.total_seconds())

        def watch_time_str(self, time_str: str) -> None:
            self.update(get_time_as_ascii_string(time_str))

    def __init__(self, task: Task) -> None:
        super().__init__()
        self.task_ = task

    def compose(self) -> ComposeResult:
        clock = self.Clock(self.task_)
        yield clock


class RecapDisplay(App):
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("j", "scroll(10)", "Scroll Down", priority=True),
        Binding("k", "scroll( -10)", "Scroll Up", priority=True),
    ]

    def __init__(self, tasks: Sequence[Task], settings: Settings) -> None:
        super().__init__()
        self.tasks = tasks
        self.settings = settings

    def action_scroll(self, y: int) -> None:
        self.screen.scroll_relative(0, y)

    def compose(self) -> ComposeResult:
        table = Table(expand=True, row_styles=["white on grey19", "white"], box=box.ROUNDED)

        for column in self.settings.recap_layout:
            table.add_column(column.header_name)

        total_duration = timedelta()
        previous_task_start = self.tasks[0].start
        for task in self.tasks:
            if self.new_section_started(previous_task_start, task.start):
                table.add_section()
            previous_task_start = task.start

            args = []
            for column in self.settings.recap_layout:
                if column.attribute == "project":
                    args.append(task.project.name)
                elif column.attribute == "task":
                    args.append(task.name)
                elif column.attribute == "note":
                    args.append(task.note)
                elif column.attribute == "start":
                    format_spec = column.options.get("format", "%d/%m/%Y %H:%M:%S")
                    args.append(to_aware_string(task.start, self.settings.tz, format_spec))
                elif column.attribute == "end":
                    format_spec = column.options.get("format", "%d/%m/%Y %H:%M:%S")
                    args.append(to_aware_string(task.end, self.settings.tz, format_spec))
                elif column.attribute == "target":
                    format_spec = column.options.get("format", "%d/%m/%Y %H:%M:%S")
                    args.append(to_aware_string(task.target, self.settings.tz, format_spec))
                elif column.attribute == "duration":
                    delta = task.end - task.start
                    total_duration += delta
                    args.append(format_seconds(delta.total_seconds()))
                elif column.attribute == "id":
                    args.append(str(task.id))

            table.add_row(*args)

        if self.settings.show_total:
            table.add_section()
            args = [""] * (len(self.settings.recap_layout) - 2)
            args += ["total", format_seconds(total_duration.total_seconds())]
            table.add_row(*args)

        yield Static(table)
        yield Footer()

    def new_section_started(self, previous_dt: datetime, next_dt: datetime) -> bool:
        if self.settings.sections == "none":
            return False
        elif self.settings.sections == "days":
            return (
                previous_dt.day != next_dt.day
                or previous_dt.month != next_dt.month
                or previous_dt.year != next_dt.year
            )
        elif self.settings.sections == "weeks":
            week_end = previous_dt + timedelta(days=6 - previous_dt.weekday())
            week_end = week_end.replace(hour=23, minute=59, second=59, microsecond=999999)
            return next_dt > week_end
        elif self.settings.sections == "months":
            return previous_dt.month != next_dt.month or previous_dt.year != next_dt.year
        else:
            raise ValueError
