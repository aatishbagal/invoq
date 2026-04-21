from __future__ import annotations

import os
from pathlib import Path

from invoq.mcp.registry import registry
from invoq.mcp.types import ToolParameter, ToolResult


@registry.register(
    name="read_file",
    description="Read the contents of a file. Returns the file content as text.",
    parameters=[
        ToolParameter("path", "string", "Path to the file to read"),
        ToolParameter("max_lines", "integer", "Maximum number of lines to read (default: 100)", required=False),
    ],
)
async def read_file(
    path: str,
    max_lines: int = 100,
) -> ToolResult:
    try:
        file_path = Path(path).expanduser().resolve()

        if not file_path.exists():
            return ToolResult(
                call_id=None,
                success=False,
                output="",
                error=f"File not found: {path}",
            )

        if not file_path.is_file():
            return ToolResult(
                call_id=None,
                success=False,
                output="",
                error=f"Not a file: {path}",
            )

        if file_path.stat().st_size > 1_000_000:
            return ToolResult(
                call_id=None,
                success=False,
                output="",
                error="File too large (>1MB). Use 'head' or 'tail' command instead.",
            )

        with open(file_path, "r", errors="replace") as f:
            if max_lines:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"\n... (truncated at {max_lines} lines)")
                        break
                    lines.append(line)
                content = "".join(lines)
            else:
                content = f.read()

        return ToolResult(
            call_id=None,
            success=True,
            output=content,
        )

    except PermissionError:
        return ToolResult(
            call_id=None,
            success=False,
            output="",
            error=f"Permission denied: {path}",
        )
    except Exception as e:
        return ToolResult(
            call_id=None,
            success=False,
            output="",
            error=str(e),
        )


@registry.register(
    name="list_directory",
    description="List contents of a directory with file types and sizes.",
    parameters=[
        ToolParameter("path", "string", "Directory path (default: current directory)", required=False),
        ToolParameter("show_hidden", "boolean", "Include hidden files (default: false)", required=False),
    ],
)
async def list_directory(
    path: str = ".",
    show_hidden: bool = False,
) -> ToolResult:
    try:
        dir_path = Path(path).expanduser().resolve()

        if not dir_path.exists():
            return ToolResult(
                call_id=None,
                success=False,
                output="",
                error=f"Directory not found: {path}",
            )

        if not dir_path.is_dir():
            return ToolResult(
                call_id=None,
                success=False,
                output="",
                error=f"Not a directory: {path}",
            )

        entries = []
        for entry in sorted(dir_path.iterdir()):
            name = entry.name

            if not show_hidden and name.startswith("."):
                continue

            try:
                stat_info = entry.stat()
                size = stat_info.st_size

                if entry.is_dir():
                    entry_type = "dir"
                    size_str = "-"
                elif entry.is_symlink():
                    entry_type = "link"
                    size_str = f"{size}B"
                else:
                    entry_type = "file"
                    if size >= 1_000_000:
                        size_str = f"{size // 1_000_000}MB"
                    elif size >= 1_000:
                        size_str = f"{size // 1_000}KB"
                    else:
                        size_str = f"{size}B"

                entries.append(f"{entry_type:5} {size_str:>8}  {name}")

            except (PermissionError, OSError):
                entries.append(f"{'?':5} {'?':>8}  {name}")

        output = f"Directory: {dir_path}\n\n"
        output += "\n".join(entries) if entries else "(empty)"

        return ToolResult(
            call_id=None,
            success=True,
            output=output,
        )

    except PermissionError:
        return ToolResult(
            call_id=None,
            success=False,
            output="",
            error=f"Permission denied: {path}",
        )
    except Exception as e:
        return ToolResult(
            call_id=None,
            success=False,
            output="",
            error=str(e),
        )


@registry.register(
    name="get_system_info",
    description="Get current system information including OS, shell, working directory, and user.",
    parameters=[],
)
async def get_system_info() -> ToolResult:
    import getpass
    import platform

    try:
        info = {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "shell": os.environ.get("SHELL", "unknown"),
            "cwd": os.getcwd(),
            "user": getpass.getuser(),
            "home": str(Path.home()),
        }

        output = "\n".join(f"{k}: {v}" for k, v in info.items())

        return ToolResult(
            call_id=None,
            success=True,
            output=output,
        )
    except Exception as e:
        return ToolResult(
            call_id=None,
            success=False,
            output="",
            error=str(e),
        )


__all__ = ["read_file", "list_directory", "get_system_info"]
