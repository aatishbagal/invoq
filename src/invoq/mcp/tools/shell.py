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
    description="""Execute a flat command list on the user's Linux system.

Use a single line of literal commands joined only by &&, for example:
echo one && echo two. Newlines, shebangs, comments, other command separators,
control syntax, functions, assignments, and expansions are blocked. Quoted or
escaped operators are literal arguments. For one command, prefer execute_command.

Every command is independently validated before any command runs. Dangerous
commands are blocked. Redirections and state-changing commands require approval;
remediation mode also requires approval for SAFE commands. Execution stops when
a command fails.""",
    parameters=[
        ToolParameter("script", "string", "Single-line literal commands joined by &&"),
        ToolParameter("working_dir", "string", "Working directory (optional)", required=False),
    ],
)
