from typing import Annotated, Optional

import typer
from rich.console import Console

from invoq import __version__

console = Console()
app = typer.Typer(name="invoq", no_args_is_help=True)

# -- subcommand groups --

config_app = typer.Typer(name="config", help="Manage configuration.", no_args_is_help=True)
app.add_typer(config_app)

extensions_app = typer.Typer(name="extensions", help="Manage extensions.", no_args_is_help=True)
app.add_typer(extensions_app)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"invoq {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-V", callback=version_callback, is_eager=True, help="Show version and exit."),
    ] = None,
) -> None:
    """invoq - A CLI tool for invoking tasks."""


@app.command()
def ask(prompt: Annotated[str, typer.Argument(help="The prompt to send.")]) -> None:
    """Send a prompt."""
    console.print(f"[bold]Prompt:[/bold] {prompt}")


@app.command()
def debug() -> None:
    """Run diagnostics."""
    console.print("[bold]Debug info[/bold]")
    console.print(f"  version: {__version__}")


@app.command()
def explain(command: Annotated[str, typer.Argument(help="The command to explain.")]) -> None:
    """Explain a command."""
    console.print(f"[bold]Explaining:[/bold] {command}")


# -- config subcommands --

@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    console.print("[bold]Configuration[/bold]")


# -- extensions subcommands --

@extensions_app.command("list")
def extensions_list() -> None:
    """List installed extensions."""
    console.print("[bold]Extensions[/bold]")


if __name__ == "__main__":
    app()
