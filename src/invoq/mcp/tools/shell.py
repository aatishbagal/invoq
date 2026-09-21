from __future__ import annotations

from typing import Optional

from invoq.mcp.capabilities import ExecutionBinding, ExecutionMode, ToolCapabilities
from invoq.mcp.registry import registry
from invoq.mcp.types import ToolCall, ToolParameter, ToolResult


async def execute_command(command: str, working_dir: Optional[str] = None) -> ToolResult:
    from invoq.mcp.server import server

    return await server.handle_tool_call(ToolCall(
        "execute_command", {"command": command, "working_dir": working_dir},
    ))


async def execute_script(script: str, working_dir: Optional[str] = None) -> ToolResult:
    from invoq.mcp.server import server

    return await server.handle_tool_call(ToolCall(
        "execute_script", {"script": script, "working_dir": working_dir},
    ))


__all__ = ["execute_command", "execute_script"]


registry.register(
    capabilities=ToolCapabilities(subprocess=True),
    validator_hook=ExecutionBinding(ExecutionMode.COMMAND, "command"),
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


registry.register(
    capabilities=ToolCapabilities(subprocess=True),
    validator_hook=ExecutionBinding(ExecutionMode.SCRIPT, "script"),
    name="execute_script",
    description="""Execute a multi-line bash script on the user's Linux system.

Use this tool for related literal commands separated by newlines or supported
shell operators. Shell variables, substitutions, and loops are blocked by the
current classification policy. For a single command, prefer execute_command.

All commands in the script are validated before execution. Dangerous commands are
blocked and the user confirms before the script runs.""",
    parameters=[
        ToolParameter("script", "string", "The bash script content"),
        ToolParameter("working_dir", "string", "Working directory (optional)", required=False),
    ],
)
