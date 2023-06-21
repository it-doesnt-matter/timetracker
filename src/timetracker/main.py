import argparse

from timetracker.commands import Commands
from timetracker.models import DB_FILE

commander = Commands(DB_FILE)

parser = argparse.ArgumentParser(prog="TimeTracker")
subparser = parser.add_subparsers(required=True)

help_text = "create a new project"
parser_create = subparser.add_parser("create", help=help_text)
help_text = "name of the new project"
parser_create.add_argument("project", type=str, help=help_text)
parser_create.set_defaults(func=commander.create)

help_text = "delete a project"
parser_delete = subparser.add_parser("delete", help=help_text)
help_text = "name of the project that should be deleted"
parser_delete.add_argument("project", type=str, help=help_text)
parser_delete.set_defaults(func=commander.delete)

help_text = "start a new task"
parser_start = subparser.add_parser("start", help=help_text)
help_text = "name of the task that should be started"
parser_start.add_argument("task", type=str, help=help_text)
help_text = "name of the project in which the task should be started"
parser_start.add_argument("project", type=str, help=help_text)
help_text = "optional note to the task"
parser_start.add_argument("-n", "--note", type=str, help=help_text)
parser_start.set_defaults(func=commander.start)

help_text = "stop the currently running task"
parser_stop = subparser.add_parser("stop", help=help_text)
parser_stop.set_defaults(func=commander.stop)

help_text = "show information about the currently running task"
parser_status = subparser.add_parser("status", help=help_text)
help_text = (
    "type of display that should be used; "
    "if this is not specified, it falls back to the settings"
)
parser_status.add_argument(
    "-d",
    "--display",
    choices=["basic", "b", "fullscreen", "f"],
    help=help_text,
)
parser_status.set_defaults(func=commander.status)

help_text = "show a recap"
parser_recap = subparser.add_parser("recap", help=help_text)
help_text = "start date of the recap; if this is ommited, all tasks are included"
parser_recap.add_argument("start", type=str, nargs="?", help=help_text)
help_text = "end date of the recap; if this is ommitted, the same data as for start is assumed"
parser_recap.add_argument("end", type=str, nargs="?", help=help_text)
help_text = "restrict the recap to tasks of a certain project"
parser_recap.add_argument("-p", "--project", type=str, help=help_text)
help_text = (
    "split the recap table into different sections; "
    "if this is not specified, it falls back to the settings"
)
parser_recap.add_argument(
    "-s",
    "--sections",
    choices=["none", "null", "days", "d", "weeks", "w", "months", "m"],
    help=help_text,
)
help_text = "show the IDs of the tasks"
parser_recap.add_argument("-i", "--id", action="store_true", help=help_text)
parser_recap.set_defaults(func=commander.recap)

help_text = "export all the tasks to a csv file"
parser_export = subparser.add_parser("export", help=help_text)
help_text = "choose between json and csv as output format"
parser_export.add_argument("file_type", choices=["json", "csv"], help=help)
parser_export.set_defaults(func=commander.export)

help_text = "change/list settings"
parser_settings = subparser.add_parser("settings", help=help_text)
help_text = "name and new value of the setting that should be changed"
parser_settings.add_argument("-s", "--set", nargs=2, help=help_text)
help_text = "list the current settings"
parser_settings.add_argument("-l", "--list", action="store_true", help=help_text)
parser_settings.set_defaults(func=commander.set_settings)

help_text = "edit an existing task/project"
parser_edit = subparser.add_parser("edit", help=help_text)
help_text = "should a task or project be modified"
parser_edit.add_argument("type", choices=["task", "t", "project", "p"], help=help_text)
help_text = "ID of the task/project that should be changed"
parser_edit.add_argument("specifier", type=str, help=help_text)
help_text = "attribute that should be changed"
parser_edit.add_argument("attribute", type=str, help=help_text)
help_text = "the new value of the attribute"
parser_edit.add_argument("value", type=str, help=help_text)
parser_edit.set_defaults(func=commander.edit)


def main() -> None:
    args = parser.parse_args()
    args.func(args)
