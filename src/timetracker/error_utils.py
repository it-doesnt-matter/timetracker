from rich import print
from rich.console import Console
from rich.panel import Panel


# todo: add `e: Exception | str` as optional parameter
def print_error_box(text: str) -> None:
    print(Panel(str(text), title="Error", border_style="red", title_align="left"))
    raise SystemExit(1)


def print_error_line(text: str) -> None:
    text = "[red]" + text
    console = Console()
    console.rule(text, style="red")
    raise SystemExit(1)
