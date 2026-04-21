from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Optional

from invoq.mcp.types import ToolCall, ToolDefinition, ToolParameter, ToolResult


ToolHandler = Callable[..., Awaitable[ToolResult]]


@dataclass
class RegisteredTool:
    definition: ToolDefinition
    handler: ToolHandler


class ToolRegistry:
    """Registry of available MCP tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, RegisteredTool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Optional[List[ToolParameter]] = None,
        handler: Optional[ToolHandler] = None,
    ) -> Callable:
        def decorator(func: ToolHandler) -> ToolHandler:
            definition = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters or [],
            )
            self._tools[name] = RegisteredTool(
                definition=definition,
                handler=func,
            )
            return func

        if handler is not None:
            return decorator(handler)
        return decorator

    def get(self, name: str) -> Optional[RegisteredTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return [tool.definition for tool in self._tools.values()]

    def to_ollama_tools(self) -> List[Dict]:
        return [tool.definition.to_ollama_format() for tool in self._tools.values()]

    async def execute(self, call: ToolCall) -> ToolResult:
        tool = self._tools.get(call.name)

        if tool is None:
            return ToolResult(
                call_id=call.call_id,
                success=False,
                output="",
                error=f"Unknown tool: {call.name}",
            )

        try:
            result = await tool.handler(**call.arguments)
            result.call_id = call.call_id
            return result
        except TypeError as e:
            return ToolResult(
                call_id=call.call_id,
                success=False,
                output="",
                error=f"Invalid arguments: {e}",
            )
        except Exception as e:
            return ToolResult(
                call_id=call.call_id,
                success=False,
                output="",
                error=str(e),
            )


registry = ToolRegistry()


__all__ = ["ToolRegistry", "RegisteredTool", "registry", "ToolHandler"]
