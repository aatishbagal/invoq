from __future__ import annotations

from typing import Dict, List, Optional

from invoq.mcp.registry import ToolRegistry, registry
from invoq.mcp.types import ToolCall, ToolDefinition, ToolResult

from invoq.mcp import tools as _tools  # noqa: F401 - import registers tools


class InvoqMCPServer:
    """MCP Server for invoq.

    Security boundary between the LLM and the system. The LLM can only
    execute operations through registered tools.
    """

    def __init__(self, tool_registry: Optional[ToolRegistry] = None) -> None:
        self.registry = tool_registry or registry

    def get_tools(self) -> List[ToolDefinition]:
        return self.registry.list_tools()

    def get_tools_for_ollama(self) -> List[Dict]:
        return self.registry.to_ollama_tools()

    async def handle_tool_call(self, call: ToolCall) -> ToolResult:
        return await self.registry.execute(call)

    async def handle_tool_calls(self, calls: List[ToolCall]) -> List[ToolResult]:
        results = []
        for call in calls:
            result = await self.handle_tool_call(call)
            results.append(result)
        return results

    def parse_ollama_tool_calls(self, response: Dict) -> List[ToolCall]:
        tool_calls: List[ToolCall] = []

        message = response.get("message", {})
        calls = message.get("tool_calls", [])

        for call in calls:
            function = call.get("function", {})
            tool_calls.append(
                ToolCall(
                    name=function.get("name", ""),
                    arguments=function.get("arguments", {}),
                    call_id=call.get("id"),
                )
            )

        return tool_calls


server = InvoqMCPServer()


__all__ = ["InvoqMCPServer", "server"]
