import csv
import json
import re
from collections.abc import Iterable
from datetime import datetime, timedelta
from importlib.abc import Traversable
from importlib.resources import files
from importlib.abc import Traversable
from pathlib import Path
from typing import Annotated, Optional
from zoneinfo import ZoneInfo

import typer
from peewee import JOIN, DoesNotExist, IntegrityError, OperationalError, fn
from pydantic import ValidationError

from .display import RecapDisplay, display_project_list, display_status
from .enums import DisplayType, FileType, TableType
from .error_utils import print_error_box
from .models import DB_FILE, Project, ProjectToTag, Tag, Task, TaskToTag, db
from .parsers import parse_date_range
from .settings import Settings
from .time_utils import format_seconds, to_aware_string

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})
try:
    # somehow model_validate_json raises a NotImplementedError
    with files("timetracker").joinpath("settings.json").open("r") as file:
        model_dict = json.load(file)
    settings = Settings.model_validate(model_dict)
except FileNotFoundError:
    settings = Settings()
except ValidationError as e:
    print_error_box("The validation of the settings failed!")


@app.callback()
def entry(db_file: Annotated[Optional[Path], typer.Option("-d", "--database")] = None) -> None:
    if db_file is None:
        db_file = DB_FILE
    db.init(db_file, pragmas={"foreign_keys": 1})


@app.command(help="create a new project")
def create(
    project_name: str, tags_as_str: Annotated[Optional[str], typer.Option("-t", "--tags")] = None
) -> None:
    tags = map(str.strip, tags_as_str.split(",")) if tags_as_str is not None else []

    try:
        with db:
            project = Project.create(name=project_name, start=datetime.utcnow())
            tag_ids = set()
            for tag in tags:
                tag_ids.add(Tag.get_or_create(name=tag)[0].id)
            for tag_id in tag_ids:
                ProjectToTag.create(project=project, tag=tag_id)
        print(f'"{project_name}" has been succesfully created!')
    except IntegrityError:
        print(f"A project, called {project_name}, does already exist!")
        raise SystemExit(1) from None
    except OperationalError:  # can occur when a table doesn't exist
        print_error_box("The database isn't initialized properly!")


@app.command()
def complete(project_name: str) -> None:
    try:
        with db:
            project = Project.get(Project.name == project_name)
            if project.end is not None:
                print(f"{project_name} is already completed")
                raise SystemExit(1)
            project.end = datetime.utcnow()
            project.save()
    except DoesNotExist:
        print(f"There's no project called {project_name}")
    except OperationalError:  # can occur when a table doesn't exist
        print_error_box("The database isn't initialized properly!")
    print(f"{project_name} is now completed")


@app.command()
def delete(project_name: str, yes: Annotated[bool, typer.Option("-y", "--yes")] = False) -> None:
    try:
        with db:
            if Project.select().count() == 1:
                print(
                    "There must be at least one project. "
                    "To delete this project, create a new one first."
                )
                raise SystemExit(1)
            project = Project.get(Project.name == project_name)
    except DoesNotExist:
        print(f'A project, named "{project_name}", does not exist!')
        raise SystemExit(1) from None
    except OperationalError:  # can occur when a table doesn't exist
        print_error_box("The database isn't initialized properly!")

    if project.tasks.count() > 0 and not yes:
        confirmation_text = (
            "This project is not empty. "
            "Deleting it, will also delete all associated tasks! "
            "Do you really want to delete it?"
        )
        if not typer.confirm(confirmation_text):
            print("The deletion has been cancelled!")
            return

    if project.delete_instance(True) == 1:
        print(f'"{project_name}" has been succesfully deleted!')

    delete_unused_tags()


def delete_unused_tags() -> None:
    task_tag_sq = TaskToTag.select().where(TaskToTag.tag_id == Tag.id)
    project_tag_sq = ProjectToTag.select().where(ProjectToTag.tag_id == Tag.id)
    Tag.delete().where(~fn.EXISTS(task_tag_sq) & ~fn.EXISTS(project_tag_sq)).execute()


@app.command("list")
def list_projects(
    all_: Annotated[bool, typer.Option("-a", "--all")] = False,
    raw: Annotated[bool, typer.Option("-r", "--raw")] = False
) -> None:
    concat_tags = fn.GROUP_CONCAT(Tag.name, ", ").alias("tags")
    try:
        with db:
            query = (Project.select(Project, concat_tags)
                            .join(ProjectToTag, JOIN.LEFT_OUTER)
                            .join(Tag, JOIN.LEFT_OUTER)
                            .group_by(Project.id))
            if not all_:
                query = query.where(Project.end.is_null())
    except OperationalError:  # can occur when a table doesn't exist
        print_error_box("The database isn't initialized properly!")

    display_project_list(raw, query, all_, settings.tz)


@app.command()
def start(
    task_name: str,
    project_name: str,
    note: Annotated[Optional[str], typer.Option("-n", "--note")] = None,
    tags_as_str: Annotated[Optional[str], typer.Option("-t", "--tags")] = None,
    until: Annotated[Optional[str], typer.Option("-u", "--until")] = None,
    for_: Annotated[Optional[str], typer.Option("-f", "--for")] = None
) -> None:
    if until is not None and for_ is not None:
        print_error_box("until and for_ are mutually exclusive")

    start = datetime.utcnow()
    target = get_target(start, settings.tz, until, for_)
    tags = map(str.strip, tags_as_str.split(",")) if tags_as_str is not None else None

    try:
        with db:
            ongoing_tasks = Task.select().where(Task.end.is_null()).count()
            if ongoing_tasks != 0:
                task = Task.get(Task.end.is_null())
                print(f'There\'s already an ongoing task, called "{task.name}"!')
                raise SystemExit(1)
            project = Project.get(Project.name == project_name)
            task = Task.create(
                name=task_name, start=start, target=target, note=note, project=project
            )
            if tags is not None:
                tag_ids = set()
                for tag in tags:
                    tag_ids.add(Tag.get_or_create(name=tag)[0].id)
                for tag_id in tag_ids:
                    TaskToTag.create(task=task, tag=tag_id)
        print(f'"{task.name}" has been succesfully started in "{project_name}"!')
    except DoesNotExist:
        print(f'A project, named "{project_name}", does not exist!')
        raise SystemExit(1) from None
    except OperationalError:  # can occur when a table doesn't exist
        print_error_box("The database isn't initialized properly!")


def get_target(start: datetime, tz: ZoneInfo, until: str, for_: str) -> datetime | None:
    pattern = re.compile(r"(?P<hour>\d{1,2})(:(?P<minute>\d{1,2}))?")
    target = None
    if until is not None:
        match = pattern.fullmatch(until)
        if not match:
            print(
                "The argument passed to --until should be in one of the following formats: "
                '"hh", "hh:mm"'
            )
            raise SystemExit(1)
        hour = int(match.group("hour"))
        minute = int(match.group("minute") or 0)
        target = start.astimezone(tz).replace(hour=hour, minute=minute)
        target = target.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        if target <= start:
            target += timedelta(days=1)
    elif for_ is not None:
        match = pattern.fullmatch(for_)
        if not match:
            print(
                "The argument passed to --for should be in one of the following formats: "
                '"hh", "hh:mm"'
            )
            raise SystemExit(1)
        hour = int(match.group("hour"))
        minute = int(match.group("minute") or 0)
        target = start + timedelta(hours=hour, minutes=minute)
    return target


@app.command()
def status(
    display: Annotated[Optional[DisplayType], typer.Option("-d", "--display")] = None
) -> None:
    try:
        with db:
            task = Task.get(Task.end.is_null())
    except DoesNotExist:
        print("There's currently no task running!")
        raise SystemExit(1) from None
    except OperationalError:  # can occur when a table doesn't exist
        print_error_box("The database isn't initialized properly!")

    type_ = display.value if display is not None else settings.status
    display_status(type_, task, settings.tz)


@app.command()
def stop() -> None:
    try:
        with db:
            task = Task.get(Task.end.is_null())
            task.end = datetime.utcnow()
            task.save()
    except DoesNotExist:
        print("There's currently no task running!")
        raise SystemExit(1) from None
    except OperationalError:  # can occur when a table doesn't exist
        print_error_box("The database isn't initialized properly!")

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


@app.command()
def recap(
    start_input: Annotated[Optional[str], typer.Argument()] = None,
    end_input: Annotated[Optional[str], typer.Argument()] = None,
    project_name: Annotated[Optional[str], typer.Option("-p", "--project")] = None,
    id_: Annotated[bool, typer.Option("-i", "--id")] = False,
    tags_as_str: Annotated[Optional[str], typer.Option("-t", "--tags")] = None,
    task_tags_as_str: Annotated[Optional[str], typer.Option("-tt", "--task_tags")] = None,
    project_tags_as_str: Annotated[Optional[str], typer.Option("-pt", "--project_tags")] = None
) -> None:
    task_tag = Tag.alias()
    project_tag = Tag.alias()
    concat_task_tags = fn.GROUP_CONCAT(task_tag.name.distinct()).alias("task_tags")
    concat_project_tags = fn.GROUP_CONCAT(project_tag.name.distinct()).alias("project_tags")
    try:
        with db:
            query = (Task.select(Task, Project, concat_task_tags, concat_project_tags)
                         .join(TaskToTag, JOIN.LEFT_OUTER)
                         .join(task_tag, JOIN.LEFT_OUTER)
                         .switch(Task)
                         .join(Project)
                         .join(ProjectToTag, JOIN.LEFT_OUTER)
                         .join(project_tag, JOIN.LEFT_OUTER)
                         .group_by(Task.id)
                         .where(Task.end.is_null(False)))

            if start_input is not None or end_input is not None:
                start, end = parse_date_range(start_input, end_input)
                query = query.where(Task.start.between(start, end) | Task.end.between(start, end))

            if project_name is not None:
                query = query.where(Project.name == project_name)

            task_tags = []
            project_tags = []
            if tags_as_str is not None:
                task_tags.extend(map(str.strip, tags_as_str.split(",")))
                project_tags.extend(map(str.strip, tags_as_str.split(",")))
            if task_tags_as_str is not None:
                task_tags.extend(map(str.strip, task_tags_as_str.split(",")))
            if project_tags_as_str is not None:
                project_tags.extend(map(str.strip, project_tags_as_str.split(",")))

            task_tag = Tag.alias()
            project_tag = Tag.alias()
            task_tags_subquery = (TaskToTag.select()
                                .join(task_tag)
                                .where(TaskToTag.task_id == Task.id)
                                .where(task_tag.name.in_(task_tags)))
            project_tags_subquery = (ProjectToTag.select()
                                .join(project_tag)
                                .where(ProjectToTag.project_id == Project.id)
                                .where(project_tag.name.in_(project_tags)))

            if len(task_tags) != 0 and len(project_tags) != 0:
                query = query.where(
                    (fn.EXISTS(task_tags_subquery)) | (fn.EXISTS(project_tags_subquery))
                )
            elif len(task_tags) != 0 and len(project_tags) == 0:
                query = query.where(fn.EXISTS(task_tags_subquery))
            elif len(task_tags) == 0 and len(project_tags) != 0:
                query = query.where(fn.EXISTS(project_tags_subquery))

    except OperationalError:  # can occur when a table doesn't exist
        print_error_box("The database isn't initialized properly!")

    if query.count() == 0:
        print("No tasks found!")
        return

    query = query.order_by(Task.start)
    app = RecapDisplay(query, settings, id_)
    app.run()


@app.command()
def export(file_type: FileType) -> None:
    task_tag = Tag.alias()
    project_tag = Tag.alias()
    concat_task_tags = fn.GROUP_CONCAT(task_tag.name.distinct()).alias("task_tags")
    concat_project_tags = fn.GROUP_CONCAT(project_tag.name.distinct()).alias("project_tags")
    try:
        with db:
            tasks = (Task.select(Task, Project, concat_task_tags, concat_project_tags)
                         .join(TaskToTag, JOIN.LEFT_OUTER)
                         .join(task_tag, JOIN.LEFT_OUTER)
                         .switch(Task)
                         .join(Project)
                         .join(ProjectToTag, JOIN.LEFT_OUTER)
                         .join(project_tag, JOIN.LEFT_OUTER)
                         .group_by(Task.id)
                         .order_by(Task.start))
    except OperationalError:  # can occur when a table doesn't exist
        print_error_box("The database isn't initialized properly!")

    file_name = datetime.now(settings.tz).strftime("%d-%m-%Y_%H-%M-%S")
    file_path = files("timetracker").joinpath(file_name)

    if file_type.value == "csv":
        file_path = file_path.with_suffix(".csv")
        write_tasks_to_csv(tasks, file_path)
    elif file_type.value == "json":
        file_path = file_path.with_suffix(".json")
        write_tasks_to_json(tasks, file_path)
    else:
        raise ValueError

    print("A list with all completed tasks has been exported!")


def write_tasks_to_csv(tasks: Iterable[Task], path: Path | Traversable) -> None:
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "ID",
            "Project",
            "Project Tags",
            "Task",
            "Task Tags",
            "Note",
            "Start",
            "End",
            "Target",
            "Duration",
        ])
        for task in tasks:
            if task.end is None:
                continue
            delta = task.end - task.start
            duration = format_seconds(delta.total_seconds())
            writer.writerow([
                task.id,
                task.project.name,
                task.project_tags,
                task.name,
                task.task_tags,
                task.note,
                to_aware_string(task.start, settings.tz),
                to_aware_string(task.end, settings.tz),
                to_aware_string(task.target, settings.tz),
                duration,
            ])


def write_tasks_to_json(tasks: Iterable[Task], path: Path | Traversable) -> None:
    json_array = []
    for task in tasks:
        if task.end is None:
            continue
        delta = task.end - task.start
        duration = format_seconds(delta.total_seconds())
        json_array.append({
            "id": task.id,
            "project": task.project.name,
            "project_tags": task.project_tags,
            "task": task.name,
            "task_tags": task.task_tags,
            "note": task.note,
            "start": to_aware_string(task.start, settings.tz),
            "end": to_aware_string(task.end, settings.tz),
            "target": to_aware_string(task.target, settings.tz),
            "duration": duration,
        })

    with path.open("w", encoding="utf-8") as file:
        json.dump(json_array, file, ensure_ascii=False, indent=2)


@app.command("settings")
def set_settings(
    set_: tuple[str, str],
    list_: Annotated[bool, typer.Option("-l", "--list")] = False
) -> None:
    if set_ is None and not list_:
        print("At least one of the two possible flags, --set or --list, must be specified!")
        return

    if set_ is not None:
        key, value = set_

        if key not in settings.model_fields:
            print(f'The setting "{key}" doesn\'t exist!')
            return

        setattr(settings, key, value)
        with files("timetracker").joinpath("settings.json").open("w") as file:
            json.dump(settings.model_dump(mode="json"), file, ensure_ascii=False, indent=2)
        print(f"{key} has been set to {value}")
        if list_:
            print()

    if list_:
        print(settings.model_dump())


@app.command()
def edit(table_type: TableType, specifier: str, attribute: str, value: str) -> None:
    value = None if value.lower() in ["none", "null"] else value

    if table_type in ["task", "t"]:
        changed = edit_task(specifier, attribute, value)
    elif table_type in ["project", "p"]:
        changed = edit_project(specifier, attribute, value)

    match changed:
        case 0:
            print("No entries have been changed")
        case 1:
            print("One entry has been updated")
        case _:
            print(f"{changed} entries have been updated")


def edit_task(id_: int, attribute: str, value: Optional[str]) -> int:
    if attribute == "tags":
        print_error_box("not yet implemented")
    try:
        with db:
            changed = (Task.update({attribute: value})
                           .where(Task.id == id_)
                           .execute())
    except OperationalError:  # can occur when a table doesn't exist
        print_error_box("The database isn't initialized properly!")

    return changed


def edit_project(name: str, attribute: str, value: Optional[str]) -> int:
    if attribute == "tags":
        print_error_box("not yet implemented")
    try:
        with db:
            changed = (Project.update({attribute: value})
                              .where(Project.name == name)
                              .execute())
    except OperationalError:  # can occur when a table doesn't exist
        print_error_box("The database isn't initialized properly!")

    return changed
