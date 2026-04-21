from __future__ import annotations

import json
import re
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
        """Parse tool calls from Ollama response.

        Handles two formats:
        1. Native tool_calls field (newer models)
        2. JSON in message.content (qwen2.5-coder and similar)
        """
        tool_calls: List[ToolCall] = []
        message = response.get("message", {})

        # Method 1: native tool_calls field
        native_calls = message.get("tool_calls", [])
        if native_calls:
            for call in native_calls:
                function = call.get("function", {})
                tool_calls.append(
                    ToolCall(
                        name=function.get("name", ""),
                        arguments=function.get("arguments", {}),
                        call_id=call.get("id"),
                    )
                )
            return tool_calls

        # Method 2: parse JSON from content
        content = message.get("content", "")
        if content:
            parsed = self._parse_tool_call_from_content(content)
            if parsed:
                tool_calls.append(parsed)

        return tool_calls

    def _parse_tool_call_from_content(self, content: str) -> Optional[ToolCall]:
        """Try to extract a tool call from message content.

        Handles formats like:
        - {"name": "tool_name", "arguments": {...}}
        - ```json\n{"name": "tool_name", "arguments": {...}}\n```
        """
        content = content.strip()

        if content.startswith("```"):
            match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
            if match:
                content = match.group(1).strip()

        try:
            data = json.loads(content)
            if isinstance(data, dict) and "name" in data:
                name = data.get("name", "")
                arguments = data.get("arguments", {})
                if self.registry.get(name):
                    return ToolCall(
                        name=name,
                        arguments=arguments if isinstance(arguments, dict) else {},
                        call_id=None,
                    )
        except json.JSONDecodeError:
            pass

        json_match = re.search(
            r'\{[^{}]*"name"\s*:\s*"[^"]+"[^{}]*"arguments"\s*:\s*\{[^{}]*\}[^{}]*\}',
            content,
        )
        if json_match:
            try:
                data = json.loads(json_match.group())
                name = data.get("name", "")
                if self.registry.get(name):
                    return ToolCall(
                        name=name,
                        arguments=data.get("arguments", {}),
                        call_id=None,
                    )
            except json.JSONDecodeError:
                pass

        return None


server = InvoqMCPServer()


__all__ = ["InvoqMCPServer", "server"]
