import asyncio
import shutil
import subprocess
import sys
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.prompt import Confirm

from invoq import __version__
from invoq.config import is_first_run

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
    ctx: typer.Context,
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-V", callback=version_callback, is_eager=True, help="Show version and exit."),
    ] = None,
) -> None:
    """invoq - A CLI tool for invoking tasks."""
    invoked = ctx.invoked_subcommand
    if is_first_run() and invoked not in ("setup", "config"):
        console.print("[yellow]First time? Run 'invoq setup' to get started.[/yellow]")
        console.print()


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


@app.command("self-update")
def self_update() -> None:
    """Update invoq to the latest version."""
    console.print("Checking for updates...")

    try:
        if shutil.which("pipx"):
            subprocess.run(["pipx", "upgrade", "invoq"], check=True)
        else:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--user", "--upgrade", "invoq"],
                check=True,
            )
        console.print("[green]Updated to latest version.[/green]")
    except subprocess.CalledProcessError:
        console.print("[red]Update failed. Try running manually:[/red]")
        if shutil.which("pipx"):
            console.print("  pipx upgrade invoq")
        else:
            console.print("  pip install --user --upgrade invoq")
        raise typer.Exit(1)


@app.command("self-uninstall")
def self_uninstall() -> None:
    """Uninstall invoq from your system."""
    console.print("This will remove invoq from your system.")

    if not Confirm.ask("Continue?", default=False):
        console.print("Cancelled.")
        raise typer.Exit(0)

    try:
        if shutil.which("pipx"):
            subprocess.run(["pipx", "uninstall", "invoq"], check=True)
        else:
            subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "invoq", "-y"],
                check=True,
            )
        console.print("[green]invoq has been removed.[/green]")
        console.print()
        console.print("To also remove config and data:")
        console.print("  rm -rf ~/.config/invoq ~/.local/share/invoq")
    except subprocess.CalledProcessError:
        console.print("[red]Uninstall failed. Try running manually:[/red]")
        if shutil.which("pipx"):
            console.print("  pipx uninstall invoq")
        else:
            console.print("  pip uninstall invoq")
        raise typer.Exit(1)


@app.command()
def setup(
    skip_checks: Annotated[
        bool, typer.Option("--skip-checks", "-s", help="Skip system requirement checks.")
    ] = False,
    model: Annotated[
        Optional[str], typer.Option("--model", "-m", help="Specify model directly, skip selection.")
    ] = None,
) -> None:
    """Interactive setup wizard for first-time configuration."""
    from invoq.cli.setup_command import run_setup

    success = asyncio.run(run_setup(skip_system_check=skip_checks, model=model))
    if not success:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
