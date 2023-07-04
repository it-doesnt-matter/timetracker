import csv
import json
import re
import sys
from argparse import Namespace
from collections.abc import Iterable
from datetime import datetime, timedelta
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from peewee import DoesNotExist, IntegrityError, OperationalError, SqliteDatabase
from rich.prompt import Confirm

from .display import RecapDisplay, display_status
from .error_utils import print_error_line
from .models import Project, Task
from .parsers import parse_date_range
from .settings import Settings
from .time_utils import format_seconds, to_aware_string


class Commands:
    def __init__(self, db_file: str | Traversable) -> None:
        self.db = SqliteDatabase(db_file, pragmas={"foreign_keys": 1})
        try:
            # somehow model_validate_json raises a NotImplementedError
            with files("timetracker").joinpath("settings.json").open("r") as file:
                model_dict = json.load(file)
            self.settings = Settings.model_validate(model_dict)
        except FileNotFoundError:
            self.settings = Settings()

    def write_settings(self) -> None:
        with files("timetracker").joinpath("settings.json").open("w") as file:
            json.dump(self.settings.model_dump(mode="json"), file, ensure_ascii=False, indent=2)

    def create(self, args: Namespace) -> None:
        try:
            with self.db:
                Project.create(name=args.project)
            print(f'"{args.project}" has been succesfully created!')
        except IntegrityError:
            print(f"A project, called {args.project}, does already exist!")
        except OperationalError:  # can occur when a table doesn't exist
            print_error_line("The database isn't initialized properly!")

    def delete(self, args: Namespace) -> None:
        try:
            with self.db:
                if Project.select().count() == 1:
                    print(
                        "There must be at least one project. "
                        "To delete this project, create a new one first."
                    )
                    return
                pr = Project.get(Project.name == args.project)
        except DoesNotExist:
            print(f'A project, named "{args.project}", does not exist!')
            sys.exit(1)
        except OperationalError:  # can occur when a table doesn't exist
            print_error_line("The database isn't initialized properly!")
            sys.exit(1)

        if pr.tasks.count() > 0:
            confirmation_text = (
                "This project is not empty. "
                "Deleting it, will also delete all associated tasks! "
                "Do you really want to delete it?"
            )
            if not Confirm.ask(confirmation_text, default=False):
                return

        if pr.delete_instance(True) == 1:
            print(f'"{args.project}" has been succesfully deleted!')

    def start(self, args: Namespace) -> None:
        start = datetime.utcnow()
        pattern = re.compile(r"(?P<hour>\d{1,2})(:(?P<minute>\d{1,2}))?")
        target = None
        if args.until is not None:
            match = pattern.fullmatch(args.until)
            if not match:
                print(
                    "The argument passed to --until should be in one of the following formats: "
                    '"hh", "hh:mm"'
                )
                return
            hour = int(match.group("hour"))
            minute = int(match.group("minute") or 0)
            target = start.astimezone(self.settings.tz).replace(hour=hour, minute=minute)
            target = target.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            if target <= start:
                target += timedelta(days=1)
        elif args.for_ is not None:
            match = pattern.fullmatch(args.for_)
            if not match:
                print(
                    "The argument passed to --for should be in one of the following formats: "
                    '"hh", "hh:mm"'
                )
                return
            hour = int(match.group("hour"))
            minute = int(match.group("minute") or 0)
            target = start + timedelta(hours=hour, minutes=minute)

        try:
            with self.db:
                ongoing_tasks = Task.select().where(Task.end.is_null()).count()
                if ongoing_tasks != 0:
                    task = Task.get(Task.end.is_null())
                    print(f'There\'s already an ongoing task, called "{task.name}"!')
                    return
                pr = Project.get(Project.name == args.project)
                Task.create(
                    name=args.task,
                    start=start,
                    target=target,
                    note=args.note,
                    project=pr
                )
            print(f'"{args.task}" has been succesfully started in "{args.project}"!')
        except DoesNotExist:
            print(f'A project, named "{args.project}", does not exist!')
        except OperationalError:  # can occur when a table doesn't exist
            print_error_line("The database isn't initialized properly!")

    def status(self, args: Namespace) -> None:
        try:
            with self.db:
                task = Task.get(Task.end.is_null())
        except DoesNotExist:
            print("There's currently no task running!")
            sys.exit(1)
        except OperationalError:  # can occur when a table doesn't exist
            print_error_line("The database isn't initialized properly!")
            sys.exit(1)

        type_ = args.display or self.settings.status
        display_status(type_, task, self.settings.tz)

    def stop(self, args: Namespace) -> None:  # noqa: ARG002
        try:
            with self.db:
                task = Task.get(Task.end.is_null())
                task.end = datetime.utcnow()
                task.save()
        except DoesNotExist:
            print("There's currently no task running!")
            return
        except OperationalError:  # can occur when a table doesn't exist
            print_error_line("The database isn't initialized properly!")
            sys.exit(1)

        now = datetime.utcnow()
        start_delta = now - task.start
        run_time = format_seconds(start_delta.total_seconds())
        message = f'"{task.name}" has been stopped with a run-time of {run_time}.'

        if task.target is not None:
            target_delta = task.target - now
            target_string = format_seconds(target_delta.total_seconds())
            if target_delta.total_seconds() > 0:
                message += f" It would have taken another {target_string} to reach the target."
            else:
                message += f" The target has been reached {target_string} ago."

        print(message)

    def recap(self, args: Namespace) -> None:
        try:
            with self.db:

                query = (Task.select(Task, Project)
                             .join(Project)
                             .where(Task.end.is_null(False)))

                if args.start is not None or args.end is not None:
                    start, end = parse_date_range(args.start, args.end)
                    query = query.where(
                        Task.start.between(start, end) | Task.end.between(start, end)
                    )

                if args.project is not None:
                    query = query.where(Project.name == args.project)

        except OperationalError:  # can occur when a table doesn't exist
            print_error_line("The database isn't initialized properly!")

        if query.count() == 0:
            print("No tasks found!")
            return

        query = query.order_by(Task.start)
        app = RecapDisplay(query, self.settings)
        app.run()

    def export(self, args: Namespace) -> None:
        try:
            with self.db:
                tasks = (Task.select(Task, Project)
                             .join(Project)
                             .order_by(Task.start))
        except OperationalError:  # can occur when a table doesn't exist
            print_error_line("The database isn't initialized properly!")
            sys.exit(1)

        file_name = datetime.now(self.settings.tz).strftime("%d-%m-%Y_%H-%M-%S")
        file_path = files("timetracker").joinpath(file_name)

        if args.file_type == "csv":
            file_path = file_path.with_suffix(".csv")
            self.write_tasks_to_csv(tasks, file_path)
        elif args.file_type == "json":
            file_path = file_path.with_suffix(".json")
            self.write_tasks_to_json(tasks, file_path)
        else:
            raise ValueError

        print("A list with all completed tasks has been exported!")

    def write_tasks_to_csv(self, tasks: Iterable[Task], path: Path | Traversable) -> None:
        with path.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Project", "Task", "Note", "Start", "End", "Traget", "Duration"])
            for task in tasks:
                if task.end is None:
                    continue
                delta = task.end - task.start
                duration = format_seconds(delta.total_seconds())
                writer.writerow([
                    task.project.name,
                    task.name,
                    task.note,
                    to_aware_string(task.start, self.settings.tz),
                    to_aware_string(task.end, self.settings.tz),
                    to_aware_string(task.target, self.settings.tz),
                    duration,
                ])

    def write_tasks_to_json(self, tasks: Iterable[Task], path: Path | Traversable) -> None:
        json_array = []
        for task in tasks:
            if task.end is None:
                continue
            delta = task.end - task.start
            duration = format_seconds(delta.total_seconds())
            json_array.append({
                "project": task.project.name,
                "task": task.name,
                "note": task.note,
                "start": to_aware_string(task.start, self.settings.tz),
                "end": to_aware_string(task.end, self.settings.tz),
                "target": to_aware_string(task.target, self.settings.tz),
                "duration": duration,
            })

        with path.open("w", encoding="utf-8") as file:
            json.dump(json_array, file, ensure_ascii=False, indent=2)

    def set_settings(self, args: Namespace) -> None:
        if args.set is None and not args.list:
            print("At least one of the two possible flags, --set or --list, must be specified!")
            return

        if args.set is not None:
            key, value = args.set

            if key not in self.settings.model_fields:
                print(f'The setting "{key}" doesn\'t exist!')
                return

            setattr(self.settings, key, value)
            self.write_settings()
            print(f"{key} has been set to {value}")
            if args.list:
                print()

        if args.list:
            print(self.settings.model_dump())

    def edit(self, args: Namespace) -> None:
        value = None if args.value.lower() in ["none", "null"] else args.value

        if args.type in ["task", "t"]:
            self.edit_task(args.specifier, args.attribute, value)
        elif args.type in ["project", "p"]:
            self.edit_project(args.specifier, args.attribute, value)

    def edit_task(self, id_: int, attribute: str, value: Optional[str]) -> None:
        try:
            with self.db:
                changed = (Task.update({attribute: value})
                               .where(Task.id == id_)
                               .execute())
        except OperationalError:  # can occur when a table doesn't exist
            print_error_line("The database isn't initialized properly!")

        match changed:
            case 0:
                print("No entries have been changed")
            case 1:
                print("One entry has been updated")
            case _:
                print(f"{changed} entries have been updated")

    def edit_project(self, name: str, attribute: str, value: Optional[str]) -> None:
        try:
            with self.db:
                q = (Project
                     .update({attribute: value})
                     .where(Project.name == name))
                q.execute()
        except OperationalError:  # can occur when a table doesn't exist
            print_error_line("The database isn't initialized properly!")
