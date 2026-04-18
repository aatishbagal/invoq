from __future__ import annotations

from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.text import Text

from invoq.core.tiers import CommandTier
from invoq.core.validator import ValidationResult

console = Console()


_TIER_STYLES = {
    CommandTier.SAFE: "green",
    CommandTier.CONFIRM: "yellow",
    CommandTier.BLOCKED: "red",
    CommandTier.UNKNOWN: "red",
}


def display_command_panel(command: str, is_script: bool = False) -> None:
    if is_script:
        body = Syntax(command, "bash", theme="ansi_dark", line_numbers=True, word_wrap=True)
        title = "Script"
    else:
        body = Text(command, style="bold white")
        title = "Command"
    console.print(Panel(body, title=title, border_style="cyan"))


def display_validation_info(validation: ValidationResult) -> None:
    style = _TIER_STYLES.get(validation.tier, "white")
    console.print(f"  Tier: [{style}]{validation.tier.value}[/{style}]")
    if validation.commands_found:
        cmds = ", ".join(validation.commands_found)
        console.print(f"  Commands: [cyan]{cmds}[/cyan]")


def display_warnings(warnings: List[str]) -> None:
    for w in warnings:
        console.print(f"  [yellow]! {w}[/yellow]")


def display_blocked_message(reason: str) -> None:
    console.print(Panel(reason, title="Blocked", border_style="red", style="red"))


def prompt_yes_no_edit() -> str:
    while True:
        raw = Prompt.ask(
            "  Execute? [bold]\\[y][/bold]es / [bold]\\[n][/bold]o / [bold]\\[e][/bold]dit",
            default="n",
        ).strip().lower()
        if not raw:
            return "n"
        first = raw[0]
        if first in ("y", "n", "e"):
            return first
        console.print("  [red]Please enter y, n, or e.[/red]")


def prompt_yes_no(message: str, default: bool = False) -> bool:
    default_str = "y" if default else "n"
    raw = Prompt.ask(f"  {message} [y/n]", default=default_str).strip().lower()
    if not raw:
        return default
    return raw.startswith("y")


def display_execution_result(result) -> None:
    duration_s = result.duration_ms / 1000
    if result.was_timeout:
        console.print(f"  [red]Timed out after {duration_s:.1f}s[/red]")
    elif result.was_cancelled:
        console.print("  [yellow]Cancelled.[/yellow]")
    elif result.was_blocked:
        console.print(f"  [red]Blocked: {result.block_reason}[/red]")
    elif result.success:
        console.print(f"  [green]Done[/green] in {duration_s:.2f}s")
    else:
        console.print(f"  [red]Failed[/red] (exit {result.exit_code}) in {duration_s:.2f}s")


def display_cancelled() -> None:
    console.print("  [yellow]Cancelled.[/yellow]")
