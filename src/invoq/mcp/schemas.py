from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# Input schemas

class ExecuteCommandInput(BaseModel):
    command: str = Field(
        ...,
        description="Shell command to execute",
        max_length=1000,
    )
    working_dir: Optional[str] = Field(
        None,
        description="Working directory for command execution",
    )


class ExecuteScriptInput(BaseModel):
    script: str = Field(
        ...,
        description="Bash script content to execute",
        max_length=10000,
    )
    working_dir: Optional[str] = Field(
        None,
        description="Working directory for script execution",
    )


class ReadFileInput(BaseModel):
    path: str = Field(
        ...,
        description="Path to the file to read",
    )
    max_lines: int = Field(
        100,
        description="Maximum number of lines to read",
        ge=1,
        le=1000,
    )


class ListDirectoryInput(BaseModel):
    path: str = Field(
        ".",
        description="Directory path to list",
    )
    show_hidden: bool = Field(
        False,
        description="Whether to show hidden files",
    )


# Output schemas

class CommandOutput(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int


class FileContent(BaseModel):
    content: str
    lines: int
    truncated: bool


class DirectoryEntry(BaseModel):
    name: str
    type: str
    size: Optional[int]


class DirectoryListing(BaseModel):
    path: str
    entries: List[DirectoryEntry]


class SystemInfo(BaseModel):
    os: str
    os_release: str
    shell: str
    cwd: str
    user: str
    home: str


__all__ = [
    "ExecuteCommandInput",
    "ExecuteScriptInput",
    "ReadFileInput",
    "ListDirectoryInput",
    "CommandOutput",
    "FileContent",
    "DirectoryEntry",
    "DirectoryListing",
    "SystemInfo",
]
