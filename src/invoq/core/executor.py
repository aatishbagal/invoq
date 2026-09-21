from __future__ import annotations

import asyncio
import os
import stat
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

from invoq.config import Config
from invoq.core.history import CommandHistory
from invoq.core.parser import extract_base_commands
from invoq.core.tiers import CommandTier
from invoq.core.validator import CommandValidator, ValidationResult
from invoq.ui.confirmation import (
    display_cancelled,
    display_command_panel,
    display_validation_info,
    display_warnings,
    prompt_yes_no_edit,
)


class ConfirmationChoice(Enum):
    YES = "yes"
    NO = "no"
    EDIT = "edit"


@dataclass
class ExecutionResult:
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    command: str
    duration_ms: int
    was_cancelled: bool = False
    was_timeout: bool = False
    was_blocked: bool = False
    block_reason: Optional[str] = None

    @property
    def failed(self) -> bool:
        return self.exit_code != 0

    @property
    def output(self) -> str:
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts)


@dataclass
class ScriptExecutionResult:
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    script: str
    script_path: str
    duration_ms: int
    was_cancelled: bool = False
    was_timeout: bool = False
    commands_blocked: List[str] = field(default_factory=list)


class SafeExecutor:
    """Executes commands safely with validation and confirmation."""

    def __init__(
        self,
        validator: CommandValidator,
        config: Config,
        timeout_seconds: int = 300,
        history: Optional[CommandHistory] = None,
    ) -> None:
        self.validator = validator
        self.config = config
        self.timeout = timeout_seconds
        self.history = history or CommandHistory()

    async def execute(
        self,
        command: str,
        working_dir: Optional[str] = None,
        skip_confirmation: bool = False,
        env: Optional[dict] = None,
    ) -> ExecutionResult:
        validation = self.validator.validate(command)

        if not validation.allowed:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                command=command,
                duration_ms=0,
                was_blocked=True,
                block_reason=validation.reason,
            )

        current_command = command
        current_validation = validation

        if current_validation.tier == CommandTier.CONFIRM and not skip_confirmation:
            while True:
                choice = self._prompt_confirmation(current_command, current_validation)

                if choice == ConfirmationChoice.YES:
                    break
                if choice == ConfirmationChoice.NO:
                    return ExecutionResult(
                        success=False,
                        exit_code=-1,
                        stdout="",
                        stderr="",
                        command=current_command,
                        duration_ms=0,
                        was_cancelled=True,
                    )
                if choice == ConfirmationChoice.EDIT:
                    edited = self._edit_command(current_command)
                    if edited is None or not edited.strip():
                        return ExecutionResult(
                            success=False,
                            exit_code=-1,
                            stdout="",
                            stderr="",
                            command=current_command,
                            duration_ms=0,
                            was_cancelled=True,
                        )
                    current_command = edited
                    current_validation = self.validator.validate(current_command)
                    if not current_validation.allowed:
                        return ExecutionResult(
                            success=False,
                            exit_code=-1,
                            stdout="",
                            stderr="",
                            command=current_command,
                            duration_ms=0,
                            was_blocked=True,
                            block_reason=current_validation.reason,
                        )
                    if current_validation.tier != CommandTier.CONFIRM:
                        break

        exit_code, stdout, stderr, duration_ms, was_timeout = await self._run_subprocess(
            current_command, working_dir, env, is_script=False
        )

        result = ExecutionResult(
            success=(exit_code == 0 and not was_timeout),
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            command=current_command,
            duration_ms=duration_ms,
            was_timeout=was_timeout,
        )

        self.history.add(
            command=current_command,
            exit_code=result.exit_code,
            stderr=result.stderr,
            cwd=working_dir or os.getcwd(),
        )

        return result

    async def execute_script(
        self,
        script: str,
        working_dir: Optional[str] = None,
        skip_confirmation: bool = False,
    ) -> ScriptExecutionResult:
        commands = self._parse_script_commands(script)

        validation = self.validator.validate(script)
        blocked = [] if validation.allowed else [script]
        needs_confirm = validation.tier == CommandTier.CONFIRM
        if script.startswith("#!") and script.splitlines()[0] not in {
            "#!/bin/bash", "#!/bin/sh", "#!/usr/bin/env bash", "#!/usr/bin/env sh",
        }:
            blocked = [script]

        if blocked:
            return ScriptExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                script=script,
                script_path="",
                duration_ms=0,
                commands_blocked=blocked,
            )

        if needs_confirm and not skip_confirmation:
            fake_validation = ValidationResult(
                allowed=True,
                tier=CommandTier.CONFIRM,
                reason="Script requires confirmation",
                commands_found=commands,
            )
            choice = self._prompt_confirmation(script, fake_validation)
            if choice != ConfirmationChoice.YES:
                return ScriptExecutionResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    script=script,
                    script_path="",
                    duration_ms=0,
                    was_cancelled=True,
                )

        script_body = script if script.startswith("#!") else f"#!/usr/bin/env bash\nset -e\n{script}"

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False, encoding="utf-8"
        )
        try:
            tmp.write(script_body)
            tmp.flush()
            tmp.close()
            script_path = tmp.name
            os.chmod(script_path, os.stat(script_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            exit_code, stdout, stderr, duration_ms, was_timeout = await self._run_subprocess(
                script_path, working_dir, None, is_script=True
            )

            return ScriptExecutionResult(
                success=(exit_code == 0 and not was_timeout),
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                script=script,
                script_path=script_path,
                duration_ms=duration_ms,
                was_timeout=was_timeout,
            )
        finally:
            try:
                Path(tmp.name).unlink(missing_ok=True)
            except OSError:
                pass

    def _prompt_confirmation(
        self,
        command: str,
        validation: ValidationResult,
    ) -> ConfirmationChoice:
        is_script = "\n" in command
        display_command_panel(command, is_script=is_script)
        display_validation_info(validation)

        if validation.warnings:
            display_warnings(validation.warnings)

        choice = prompt_yes_no_edit()

        if choice == "y":
            return ConfirmationChoice.YES
        if choice == "e":
            return ConfirmationChoice.EDIT
        display_cancelled()
        return ConfirmationChoice.NO

    def _edit_command(self, command: str) -> Optional[str]:
        editor = os.environ.get("EDITOR", "nano")

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False, encoding="utf-8"
        )
        try:
            tmp.write(command)
            tmp.flush()
            tmp.close()

            try:
                import subprocess
                subprocess.run([editor, tmp.name], check=False)
            except (OSError, FileNotFoundError):
                return None

            with open(tmp.name, "r", encoding="utf-8") as f:
                edited = f.read().rstrip("\n")
            return edited
        finally:
            try:
                Path(tmp.name).unlink(missing_ok=True)
            except OSError:
                pass

    async def _run_subprocess(
        self,
        command: str,
        working_dir: Optional[str],
        env: Optional[dict],
        is_script: bool = False,
    ) -> tuple[int, str, str, int, bool]:
        start = time.monotonic()

        run_env = None
        if env is not None:
            run_env = os.environ.copy()
            run_env.update(env)

        if is_script:
            proc = await asyncio.create_subprocess_exec(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=run_env,
            )
        else:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=run_env,
            )

        was_timeout = False
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            was_timeout = True
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            stdout_b, stderr_b = await proc.communicate()

        duration_ms = int((time.monotonic() - start) * 1000)
        exit_code = proc.returncode if proc.returncode is not None else -1
        stdout = stdout_b.decode("utf-8", errors="replace") if stdout_b else ""
        stderr = stderr_b.decode("utf-8", errors="replace") if stderr_b else ""

        return exit_code, stdout, stderr, duration_ms, was_timeout

    def _parse_script_commands(self, script: str) -> List[str]:
        commands: List[str] = []
        buffer = ""

        for raw_line in script.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if line.endswith("\\"):
                buffer += line[:-1].rstrip() + " "
                continue

            full = buffer + line
            buffer = ""

            base_cmds = extract_base_commands(full)
            if base_cmds:
                commands.append(full)

        if buffer.strip():
            commands.append(buffer.strip())

        return commands
