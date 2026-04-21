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
    description="Execute a shell command. Only allowed commands will run. Dangerous commands like 'rm -rf' are blocked for safety.",
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
    description="Execute a multi-line bash script. All commands in the script are validated before execution.",
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
