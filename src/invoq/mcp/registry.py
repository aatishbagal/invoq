from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from invoq.mcp.capabilities import ExecutionBinding, ReadOnlyOperation, ToolCapabilities
from invoq.mcp.types import ToolCall, ToolDefinition, ToolParameter, ToolResult


ToolHandler = ReadOnlyOperation


@dataclass(frozen=True)
class RegisteredTool:
    definition: ToolDefinition
    handler: Optional[ToolHandler]
    validator_hook: Optional[ExecutionBinding]


class ToolRegistry:
    """Register reviewed read-only operations or server-mediated execution bindings."""

    def __init__(self) -> None:
        self._tools: Dict[str, RegisteredTool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Optional[List[ToolParameter]] = None,
        handler: Optional[ToolHandler] = None,
        *,
        capabilities: Optional[ToolCapabilities] = None,
        validator_hook: Optional[ExecutionBinding] = None,
    ) -> RegisteredTool:
        if type(capabilities) is not ToolCapabilities:
            raise ValueError("Every tool must declare typed capabilities")
        if type(name) is not str or not name:
            raise ValueError("Tool names must be nonempty strings")
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        parameters = list(parameters or [])
        if any(type(parameter) is not ToolParameter for parameter in parameters):
            raise ValueError("Tool parameters must be typed declarations")
        parameter_map = {parameter.name: parameter for parameter in parameters}
        if len(parameter_map) != len(parameters):
            raise ValueError("Duplicate tool parameters")
        if capabilities.subprocess:
            if type(validator_hook) is not ExecutionBinding:
                raise ValueError("Subprocess capability requires a server validator hook")
            if handler is not None:
                raise ValueError("Subprocess tools cannot supply Python handlers or read-only operations")
            parameter = parameter_map.get(validator_hook.parameter)
            if parameter is None or parameter.type != "string" or not parameter.required:
                raise ValueError("The validator hook must bind a required string parameter")
            if validator_hook.working_dir_parameter is not None:
                directory = parameter_map.get(validator_hook.working_dir_parameter)
                if directory is None or directory.type != "string":
                    raise ValueError("The validator hook must bind a declared string working directory")
        else:
            if validator_hook is not None:
                raise ValueError("A validator hook requires subprocess capability")
            if type(handler) is not ReadOnlyOperation:
                raise ValueError("Read-only tools require a reviewed operation; arbitrary Python handlers are refused")

        definition = ToolDefinition(
            name=name, description=description, parameters=parameters,
            capabilities=capabilities,
        )
        tool = RegisteredTool(definition, handler, validator_hook)
        self._tools[name] = tool
        return tool

    def get(self, name: str) -> Optional[RegisteredTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return [tool.definition for tool in self._tools.values()]

    def to_ollama_tools(self) -> List[Dict]:
        return [tool.definition.to_ollama_format() for tool in self._tools.values()]

    async def execute(self, call: ToolCall) -> ToolResult:
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolResult(call.call_id, False, "", f"Unknown tool: {call.name}")
        if tool.definition.capabilities.subprocess:
            return ToolResult(
                call.call_id, False, "",
                "BLOCKED: Subprocess tools require server-owned validation and confirmation",
            )

        from invoq.mcp.tools.filesystem import get_system_info, list_directory, read_file

        handlers = {
            ReadOnlyOperation.READ_FILE: read_file,
            ReadOnlyOperation.LIST_DIRECTORY: list_directory,
            ReadOnlyOperation.GET_SYSTEM_INFO: get_system_info,
        }
        handler = handlers.get(tool.handler)
        if handler is None:
            return ToolResult(call.call_id, False, "", "BLOCKED: Unsupported read-only operation")
        if type(call.arguments) is not dict:
            return ToolResult(call.call_id, False, "", "Invalid arguments: expected an object")
        try:
            result = await handler(**call.arguments)
            result.call_id = call.call_id
            return result
        except TypeError as exc:
            return ToolResult(call.call_id, False, "", f"Invalid arguments: {exc}")
        except Exception as exc:
            return ToolResult(call.call_id, False, "", str(exc))


registry = ToolRegistry()


__all__ = ["ToolRegistry", "RegisteredTool", "registry", "ToolHandler"]
