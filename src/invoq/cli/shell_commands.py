import typer
from rich.console import Console
from rich.prompt import Confirm

from invoq.shell.installation import (
    SOURCE_LINE,
    get_shell_status,
    installation_plan,
    install_shell_hooks,
    uninstall_shell_hooks,
)


console = Console()
shell_app = typer.Typer(
    name="shell",
    help="Manage Linux bash and zsh failure-capture hooks.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--h", "--help"]},
)


@shell_app.command("install")
def shell_install() -> None:
    """Preview and install failed-command capture in your shell rc file."""
    try:
        plan = installation_plan()
        console.print(f"Write {plan.shell} hook script: {plan.script}", markup=False)
        console.print(f"Ensure this line exists in {plan.rc}:", markup=False)
        console.print(SOURCE_LINE, markup=False, soft_wrap=True)
        console.print("Failed-command metadata will be saved locally with private permissions.")
        console.print("Stderr is not captured; command streams and terminal behavior stay intact.")
        if not Confirm.ask("Install shell hooks?", default=False):
            console.print("Cancelled.")
            return
        install_shell_hooks()
    except (OSError, ValueError) as exc:
        console.print(f"Shell hook installation failed: {exc}", markup=False)
        raise typer.Exit(1)


@shell_app.command("uninstall")
def shell_uninstall() -> None:
    """Remove hook source lines and retire the script, preserving captured history."""
    try:
        uninstall_shell_hooks()
    except OSError as exc:
        console.print(f"Shell hook uninstall failed: {exc}", markup=False)
        raise typer.Exit(1)


@shell_app.command("status")
def shell_status() -> None:
    """Report installation and log activity without changing files."""
    try:
        status = get_shell_status()
    except OSError as exc:
        console.print(f"Cannot read shell hook status: {exc}", markup=False)
        raise typer.Exit(1)
    installed = status.script_exists and bool(status.sourced_from)
    console.print("Shell hooks: installed" if installed else "Shell hooks: not installed")
    console.print(
        f"Hook script: {'exists' if status.script_exists else 'missing'} ({status.script})",
        markup=False,
    )
    sources = ", ".join(str(rc) for rc in status.sourced_from) or "none"
    console.print(f"Source line in rc files: {sources}", markup=False)
    activity = "written within the last 24 hours" if status.log_recent else "no recent failures"
    if not status.log_exists:
        activity = "not created yet"
    console.print(f"Failure log: {activity} ({status.log})", markup=False)
    console.print("Status checks files; restart your shell after installing or uninstalling.")
