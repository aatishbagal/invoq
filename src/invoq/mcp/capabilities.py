from dataclasses import dataclass
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class ToolCapabilities:
    subprocess: bool

    def __post_init__(self) -> None:
        if type(self.subprocess) is not bool:
            raise ValueError("The subprocess capability must be a boolean")


class ReadOnlyOperation(Enum):
    READ_FILE = "read_file"
    LIST_DIRECTORY = "list_directory"
    GET_SYSTEM_INFO = "get_system_info"


class ExecutionMode(Enum):
    COMMAND = "command"
    SCRIPT = "script"


@dataclass(frozen=True)
class ExecutionBinding:
    mode: ExecutionMode
    parameter: str
    working_dir_parameter: str | None = "working_dir"

    def __post_init__(self) -> None:
        if type(self.mode) is not ExecutionMode:
            raise ValueError("An execution binding requires a valid execution mode")
        if type(self.parameter) is not str or not self.parameter:
            raise ValueError("An execution binding requires a command or script parameter")
        if self.working_dir_parameter is not None:
            if type(self.working_dir_parameter) is not str or not self.working_dir_parameter:
                raise ValueError("Invalid working directory parameter")
            if self.working_dir_parameter == self.parameter:
                raise ValueError("Execution and working directory parameters must differ")

    def bind(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if type(arguments) is not dict:
            raise ValueError("Tool arguments must be an object")
        content = arguments.get(self.parameter)
        if type(content) is not str or not content.strip():
            raise ValueError(f"Missing or invalid '{self.parameter}' argument")
        working_dir = arguments.get(self.working_dir_parameter) if self.working_dir_parameter else None
        if working_dir is not None and type(working_dir) is not str:
            raise ValueError("Working directory must be a string")
        return {self.mode.value: content, "working_dir": working_dir}
