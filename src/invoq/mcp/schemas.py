from __future__ import annotations

from copy import deepcopy
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, create_model

from invoq.mcp.capabilities import ExecutionBinding, ExecutionMode


# Input schemas

class ToolInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class ExecuteCommandInput(ToolInput):
    command: str = Field(
        ...,
        description="Shell command to execute",
        max_length=1000,
    )
    working_dir: Optional[str] = Field(
        None,
        description="Working directory for command execution",
    )


class ExecuteScriptInput(ToolInput):
    script: str = Field(
        ...,
        description="Single-line literal commands joined by &&",
        max_length=10000,
    )
    working_dir: Optional[str] = Field(
        None,
        description="Working directory for script execution",
    )


class ReadFileInput(ToolInput):
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


class ListDirectoryInput(ToolInput):
    path: str = Field(
        ".",
        description="Directory path to list",
    )
    show_hidden: bool = Field(
        False,
        description="Whether to show hidden files",
    )


class GetSystemInfoInput(ToolInput):
    pass


def execution_input_schema(binding: ExecutionBinding) -> type[ToolInput]:
    schema = ExecuteCommandInput if binding.mode == ExecutionMode.COMMAND else ExecuteScriptInput
    if binding.parameter == binding.mode.value and binding.working_dir_parameter == "working_dir":
        return schema

    fields = {}
    for name, alias in ((binding.mode.value, binding.parameter),
                        ("working_dir", binding.working_dir_parameter)):
        if alias is None:
            continue
        field = deepcopy(schema.model_fields[name])
        field.alias = alias
        field.validation_alias = alias
        field.serialization_alias = alias
        fields[name] = (field.annotation, field)
    return create_model(f"Bound{schema.__name__}", __base__=ToolInput, **fields)


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
    "ToolInput",
    "ExecuteCommandInput",
    "ExecuteScriptInput",
    "ReadFileInput",
    "ListDirectoryInput",
    "GetSystemInfoInput",
    "execution_input_schema",
    "CommandOutput",
    "FileContent",
    "DirectoryEntry",
    "DirectoryListing",
    "SystemInfo",
]
