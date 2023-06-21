import csv
import json
from argparse import Namespace
from collections.abc import Iterable
from datetime import datetime
from importlib.resources import files
from pathlib import Path
from typing import Optional

from peewee import DoesNotExist, IntegrityError, OperationalError, SqliteDatabase
from rich.prompt import Confirm

from timetracker.display import RecapDisplay, StatusDisplay, display_updating_time, format_seconds
from timetracker.models import Project, Task
from timetracker.parsers import parse_date_range, to_aware_string
from timetracker.settings import Settings


class Commands:
    def __init__(self, db_file: str) -> None:
        self.db = SqliteDatabase(db_file, pragmas={"foreign_keys": 1})
        self.settings = Settings()
        self.settings.load_settings()

    def create(self, args: Namespace) -> None:
        try:
            with self.db:
                Project.create(name=args.project)
            print(f'"{args.project}" has been succesfully created!')
        except IntegrityError:
            print(f"A project, called {args.project}, does already exist!")
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

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
            return
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")
            return

        if pr.tasks.count() > 0:
            confirmation_text = (
                "This project is not empty."
                "Deleting it, will also delete the contained tasks! "
                "Do you really want to delete it?"
            )
            if not Confirm.ask(confirmation_text, default=False):
                return

        if pr.delete_instance(True) == 1:
            print(f'"{args.project}" has been succesfully deleted!')

    def start(self, args: Namespace) -> None:
        try:
            with self.db:
                ongoing_tasks = Task.select().where(Task.end.is_null()).count()
                if ongoing_tasks != 0:
                    task = Task.get(Task.end.is_null())
                    print(f'There\'s already an ongoing task, called "{task.name}"!')
                    return
                pr = Project.get(Project.name == args.project)
                Task.create(name=args.task, start=datetime.utcnow(), project=pr, note=args.note)
            print(f'"{args.task}" has been succesfully started in "{args.project}"!')
        except DoesNotExist:
            print(f'A project, named "{args.project}", does not exist!')
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

    def status(self, args: Namespace) -> None:
        try:
            with self.db:
                task = Task.get(Task.end.is_null())
        except DoesNotExist:
            print("There's currently no task running!")
            return
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")
            return

        display = args.display or self.settings.status.value
        if display in ["basic", "b"]:
            display_updating_time(task.start, task.name, task.project.name)
        elif display in ["fullscreen", "f"]:
            app = StatusDisplay(task.start, task.name, task.project.name)
            app.run()

    def stop(self, args: Namespace) -> None:  # noqa: ARG002
        try:
            with self.db:
                task = Task.get(Task.end.is_null())
                task.end = datetime.utcnow()
                task.save()
            print(f'"{task.name}" has been stopped!')
        except DoesNotExist:
            print("There's currently no task running!")
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

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
            print("The database isn't initialized properly!")

        if query.count() == 0:
            print("No tasks found!")
            return

        if args.sections is None:
            sections = self.settings.sections.value
        else:
            sections = self.settings.sections.parse(args.sections)

        query = query.order_by(Task.start)
        app = RecapDisplay(query, self.settings.tz.value, sections, args.id)
        app.run()

    def export(self, args: Namespace) -> None:
        try:
            with self.db:
                tasks = (Task.select(Task, Project)
                             .join(Project)
                             .order_by(Task.start))
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")
            return

        file_name = datetime.now(self.settings.tz.value).strftime("%d-%m-%Y_%H-%M-%S")
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

    def write_tasks_to_csv(self, tasks: Iterable[Task], path: Path) -> None:
        with path.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Project", "Task", "Note", "Start", "End", "Duration"])
            for task in tasks:
                if task.end is None:
                    continue
                delta = task.end - task.start
                duration = format_seconds(delta.total_seconds())
                writer.writerow([
                    task.project.name,
                    task.name,
                    task.note,
                    to_aware_string(task.start, self.settings.tz.value),
                    to_aware_string(task.end, self.settings.tz.value),
                    duration,
                ])

    def write_tasks_to_json(self, tasks: Iterable[Task], path: Path) -> None:
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
                "start": to_aware_string(task.start, self.settings.tz.value),
                "end": to_aware_string(task.end, self.settings.tz.value),
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

            if not hasattr(self.settings, key):
                print(f'The setting "{key}" doesn\'t exist!')
                return

            self.settings.set_attribute(key, value)
            self.settings.write()
            print(f"{key} has been set to {value}")
            if args.list:
                print()

        if args.list:
            self.settings.show_current_config()

    def edit(self, args: Namespace) -> None:
        value = None if args.value.lower() in ["none", "null"] else args.value

        if args.type in ["task", "t"]:
            self.edit_task(args.specifier, args.attribute, value)
        elif args.type in ["project", "p"]:
            self.edit_project(args.specifier, args.attribute, value)

    def edit_task(self, id_: int, attribute: str, value: Optional[str]) -> None:
        try:
            with self.db:
                q = (Task
                     .update({attribute: value})
                     .where(Task.id == id_))
                q.execute()
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")

    def edit_project(self, name: str, attribute: str, value: Optional[str]) -> None:
        try:
            with self.db:
                q = (Project
                     .update({attribute: value})
                     .where(Project.name == name))
                q.execute()
        except OperationalError:  # can occur when a table doesn't exist
            print("The database isn't initialized properly!")
