from rich import print
from rich.console import Console
from rich.panel import Panel


def print_error_box(e: Exception | str, title: str) -> None:
    print(Panel(str(e), title=title, border_style="red"))


def print_error_line(text: str) -> None:
    text = "[red]" + text
    console = Console()
    console.rule(text, style="red")
