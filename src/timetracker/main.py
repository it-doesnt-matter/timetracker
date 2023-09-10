import json
from importlib.resources import files
from typing import Annotated

import typer

from .commands import app as commands_app

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})
app.registered_commands += commands_app.registered_commands
app.registered_callback = commands_app.registered_callback

# add help texts to commands and arguments
with files("timetracker").joinpath("help.json").open("r") as file:
    _help = json.load(file)

for function in app.registered_commands:
    function_name = function.callback.__name__
    function.help = _help[function_name]["help"]

    annotations = function.callback.__annotations__
    for key in annotations:
        if key == "return":
            continue
        if not hasattr(annotations[key], "__metadata__"):
            annotations[key] = Annotated[annotations[key], typer.Argument()]
        annotations[key].__metadata__[0].help = _help[function_name]["parameters"][key]

callback = app.registered_callback
callback_name = callback.callback.__name__
annotations = callback.callback.__annotations__
for key in annotations:
    if key == "return":
        continue
    if not hasattr(annotations[key], "__metadata__"):
        annotations[key] = Annotated[annotations[key], typer.Argument()]
    annotations[key].__metadata__[0].help = _help[callback_name]["parameters"][key]
