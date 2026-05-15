from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from typing import List, Optional

from invoq.core.tiers import CommandTier
from invoq.core.validator import CommandValidator, ValidationResult


_TIER_RANK = {
    CommandTier.SAFE: 0,
    CommandTier.CONFIRM: 1,
    CommandTier.BLOCKED: 2,
    CommandTier.UNKNOWN: 3,
}

console = Console()


class ConfirmationResult(Enum):
    APPROVED = "approved"
    DENIED = "denied"
    EDITED = "edited"


@dataclass
class ConfirmationResponse:
    result: ConfirmationResult
    edited_command: Optional[str] = None


class ConfirmationHandler:
    def __init__(self, validator: CommandValidator) -> None:
        self.validator = validator

    def _render_command_panel(
        self,
        command: str,
        validation: ValidationResult,
        working_dir: Optional[str] = None,
    ) -> None:
        panel = Panel(
            Text(command, style="bold yellow"),
            title="[bold]execute_command[/bold]",
            subtitle=f"[cyan]tier: {validation.tier.value}[/cyan]",
            box=box.ROUNDED,
            border_style="yellow",
            expand=False,
        )
        console.print(panel)
        if working_dir:
            console.print(f"  [dim]dir:[/dim] {working_dir}")
        if validation.commands_found:
            console.print(
                f"  [dim]uses:[/dim] {', '.join(validation.commands_found)}"
            )
        if validation.warnings:
            for w in validation.warnings:
                console.print(f"  [yellow]! {w}[/yellow]")

    async def request_confirmation(
        self,
        command: str,
        working_dir: Optional[str] = None,
    ) -> ConfirmationResponse:
        validation = self.validator.validate(command)

        if not validation.allowed:
            console.print(f"[red]BLOCKED:[/red] {validation.reason}")
            return ConfirmationResponse(result=ConfirmationResult.DENIED)

        if validation.tier == CommandTier.SAFE:
            return ConfirmationResponse(result=ConfirmationResult.APPROVED)

        self._render_command_panel(command, validation, working_dir)
        console.print()

        while True:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: console.input(
                    "[bold]Run this?[/bold] [green]\\[y][/green]es / "
                    "[red]\\[n][/red]o / [yellow]\\[e][/yellow]dit: "
                ).strip().lower(),
            )

            if response in ("y", "yes", ""):
                return ConfirmationResponse(result=ConfirmationResult.APPROVED)

            if response in ("n", "no"):
                console.print("[dim]Cancelled.[/dim]")
                return ConfirmationResponse(result=ConfirmationResult.DENIED)

            if response in ("e", "edit"):
                edited = await self._open_editor(command)
                if edited and edited.strip() != command.strip():
                    console.print(f"[dim]Edited to:[/dim] [yellow]{edited}[/yellow]")
                    new_validation = self.validator.validate(edited)
                    if not new_validation.allowed:
                        console.print(
                            f"[red]Edited command is blocked:[/red] "
                            f"{new_validation.reason}"
                        )
                        return ConfirmationResponse(result=ConfirmationResult.DENIED)
                    return ConfirmationResponse(
                        result=ConfirmationResult.EDITED,
                        edited_command=edited,
                    )
                return ConfirmationResponse(result=ConfirmationResult.APPROVED)

            console.print("[dim]Please enter y, n, or e.[/dim]")

    async def request_script_confirmation(
        self,
        script: str,
        parsed_commands: List[str],
        working_dir: Optional[str] = None,
    ) -> ConfirmationResponse:
        highest_tier = CommandTier.SAFE
        blocked_cmd: Optional[str] = None
        blocked_reason: Optional[str] = None

        for cmd in parsed_commands:
            v = self.validator.validate(cmd)
            if not v.allowed:
                blocked_cmd = cmd
                blocked_reason = v.reason
                break
            if _TIER_RANK[v.tier] > _TIER_RANK[highest_tier]:
                highest_tier = v.tier

        if blocked_cmd is not None:
            console.print(
                f"[red]BLOCKED:[/red] script contains blocked command "
                f"[bold]{blocked_cmd}[/bold] ({blocked_reason})"
            )
            return ConfirmationResponse(result=ConfirmationResult.DENIED)

        if highest_tier == CommandTier.SAFE:
            return ConfirmationResponse(result=ConfirmationResult.APPROVED)

        self._render_script_panel(script, highest_tier, parsed_commands, working_dir)
        console.print()

        while True:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: console.input(
                    "[bold]Run this script?[/bold] [green]\\[y][/green]es / "
                    "[red]\\[n][/red]o: "
                ).strip().lower(),
            )

            if response in ("y", "yes", ""):
                return ConfirmationResponse(result=ConfirmationResult.APPROVED)
            if response in ("n", "no"):
                console.print("[dim]Cancelled.[/dim]")
                return ConfirmationResponse(result=ConfirmationResult.DENIED)
            console.print("[dim]Please enter y or n.[/dim]")

    def _render_script_panel(
        self,
        script: str,
        tier: CommandTier,
        parsed_commands: List[str],
        working_dir: Optional[str] = None,
    ) -> None:
        panel = Panel(
            Text(script, style="white"),
            title="[bold]execute_script[/bold]",
            subtitle=f"[cyan]tier: {tier.value}[/cyan]",
            box=box.ROUNDED,
            border_style="yellow",
            expand=False,
        )
        console.print(panel)
        if working_dir:
            console.print(f"  [dim]dir:[/dim] {working_dir}")
        if parsed_commands:
            console.print(f"  [dim]commands:[/dim] {len(parsed_commands)}")

    async def _open_editor(self, command: str) -> str:
        editor = os.environ.get("EDITOR", "nano")

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".sh",
            delete=False,
            prefix="invoq_",
        ) as f:
            f.write(command)
            tmp_path = f.name

        try:
            subprocess.run([editor, tmp_path], check=True)
            with open(tmp_path, "r") as f:
                return f.read().strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return command
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


__all__ = [
    "ConfirmationHandler",
    "ConfirmationResult",
    "ConfirmationResponse",
]
