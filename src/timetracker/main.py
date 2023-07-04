import argparse
import sys

from pydantic import ValidationError

from .commands import Commands
from .error_utils import print_error_box
from .models import DB_FILE

try:
    commander = Commands(DB_FILE)
except ValidationError as e:
    print_error_box(e, "The validation of the settings failed!")
    sys.exit(1)

parser = argparse.ArgumentParser(prog="TimeTracker")
subparser = parser.add_subparsers(required=True)

parser_create = subparser.add_parser(
    "create",
    help="create a new project")
parser_create.add_argument(
    "project",
    type=str,
    help="name of the new project")
parser_create.set_defaults(func=commander.create)

parser_delete = subparser.add_parser(
    "delete",
    help="delete a project")
parser_delete.add_argument(
    "project",
    type=str,
    help="name of the project that should be deleted")
parser_delete.set_defaults(func=commander.delete)

parser_start = subparser.add_parser(
    "start",
    help="start a new task")
parser_start.add_argument(
    "task",
    type=str,
    help="name of the task that should be started")
parser_start.add_argument(
    "project",
    type=str,
    help="name of the project in which the task should be started")
parser_start.add_argument(
    "-n", "--note",
    type=str,
    help="optional note to the task")
target_group = parser_start.add_mutually_exclusive_group()
target_group.add_argument(
    "-u", "--until",
    type=str,
    help="until what time you intend to do the task")
target_group.add_argument(
    "-f", "--for",
    type=str, dest="for_",
    help="for how long do you intend to do the task")
parser_start.set_defaults(func=commander.start)

parser_stop = subparser.add_parser(
    "stop",
    help="stop the currently running task")
parser_stop.set_defaults(func=commander.stop)

parser_status = subparser.add_parser(
    "status",
    help="show information about the currently running task")
parser_status.add_argument(
    "-d", "--display",
    choices=["basic", "b", "fullscreen", "f"],
    help="type of display that should be used; if this is not specified, it falls back to the settings")
parser_status.set_defaults(func=commander.status)

parser_recap = subparser.add_parser(
    "recap",
    help="show a recap")
parser_recap.add_argument(
    "start",
    type=str, nargs="?",
    help="start date of the recap; if this is ommited, all tasks are included")
parser_recap.add_argument(
    "end",
    type=str, nargs="?",
    help="end date of the recap; if this is ommitted, the same data as for start is assumed")
parser_recap.add_argument(
    "-p", "--project",
    type=str,
    help="restrict the recap to tasks of a certain project")
parser_recap.add_argument(
    "-i", "--id",
    action="store_true",
    help="show the IDs of the tasks")
parser_recap.set_defaults(func=commander.recap)

parser_export = subparser.add_parser(
    "export",
    help="export all the tasks to a csv file")
parser_export.add_argument(
    "file_type",
    choices=["json", "csv"],
    help="choose between json and csv as output format")
parser_export.set_defaults(func=commander.export)

parser_settings = subparser.add_parser(
    "settings",
    help="change/list settings")
parser_settings.add_argument(
    "-s", "--set",
    nargs=2,
    help="name and new value of the setting that should be changed")
parser_settings.add_argument(
    "-l", "--list",
    action="store_true",
    help="list the current settings")
parser_settings.set_defaults(func=commander.set_settings)

parser_edit = subparser.add_parser(
    "edit",
    help="edit an existing task/project")
parser_edit.add_argument(
    "type",
    choices=["task", "t", "project", "p"],
    help="should a task or project be modified")
parser_edit.add_argument(
    "specifier",
    type=str,
    help="ID of the task/project that should be changed")
parser_edit.add_argument(
    "attribute",
    type=str,
    help="attribute that should be changed")
parser_edit.add_argument(
    "value",
    type=str,
    help="the new value of the attribute")
parser_edit.set_defaults(func=commander.edit)


def main() -> None:
    args = parser.parse_args()
    args.func(args)
