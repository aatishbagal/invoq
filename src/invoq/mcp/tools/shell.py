from __future__ import annotations

from typing import Optional

from invoq.config import load_config
from invoq.core.executor import SafeExecutor
from invoq.core.validator import CommandValidator
from invoq.mcp.registry import registry
from invoq.mcp.types import ToolParameter, ToolResult


_executor: Optional[SafeExecutor] = None


def get_executor() -> SafeExecutor:
    global _executor
    if _executor is None:
        config = load_config()
        validator = CommandValidator()
        _executor = SafeExecutor(validator, config)
    return _executor


@registry.register(
    name="execute_command",
    description="""Execute a shell command on the user's Linux system.

Use this tool when the user asks to:
- Run any shell command (ls, cat, grep, find, etc.)
- Check system status (df, free, top, ps)
- Manipulate files (cp, mv, mkdir, touch)
- Work with git, docker, npm, pip, etc.

The command will be validated for safety. Dangerous commands like 'rm -rf' are blocked.
The user will be asked to confirm before execution.

Examples:
- List files: execute_command({"command": "ls -la"})
- Find Python files: execute_command({"command": "find . -name '*.py'"})
- Check disk space: execute_command({"command": "df -h"})""",
    parameters=[
        ToolParameter("command", "string", "The shell command to execute"),
        ToolParameter("working_dir", "string", "Working directory (optional)", required=False),
    ],
)
async def execute_command(
    command: str,
    working_dir: Optional[str] = None,
) -> ToolResult:
    executor = get_executor()

    result = await executor.execute(
        command=command,
        working_dir=working_dir,
        skip_confirmation=False,
    )

    if result.was_blocked:
        return ToolResult(
            call_id=None,
            success=False,
            output="",
            error=f"BLOCKED: {result.block_reason}",
        )

    if result.was_cancelled:
        return ToolResult(
            call_id=None,
            success=False,
            output="",
            error="Command cancelled by user",
        )

    output = result.stdout
    if result.stderr:
        output += f"\nSTDERR: {result.stderr}"

    return ToolResult(
        call_id=None,
        success=result.success,
        output=output,
        error=result.stderr if result.failed else None,
    )


@registry.register(
    name="execute_script",
    description="""Execute a multi-line bash script on the user's Linux system.

Use this tool when a task requires multiple related commands that must run together,
for example a series of steps that depend on shell variables, pipes across multiple
lines, or loops. For a single command, prefer execute_command.

All commands in the script are validated before execution. Dangerous commands are
blocked and the user confirms before the script runs.""",
    parameters=[
        ToolParameter("script", "string", "The bash script content"),
        ToolParameter("working_dir", "string", "Working directory (optional)", required=False),
    ],
)
async def execute_script(
    script: str,
    working_dir: Optional[str] = None,
) -> ToolResult:
    executor = get_executor()

    result = await executor.execute_script(
        script=script,
        working_dir=working_dir,
        skip_confirmation=False,
    )

    if result.commands_blocked:
        return ToolResult(
            call_id=None,
            success=False,
            output="",
            error=f"BLOCKED: Script contains blocked commands: {', '.join(result.commands_blocked)}",
        )

    if result.was_cancelled:
        return ToolResult(
            call_id=None,
            success=False,
            output="",
            error="Script cancelled by user",
        )

    output = result.stdout
    if result.stderr:
        output += f"\nSTDERR: {result.stderr}"

    return ToolResult(
        call_id=None,
        success=result.success,
        output=output,
        error=result.stderr if not result.success else None,
    )


__all__ = ["execute_command", "execute_script", "get_executor"]
