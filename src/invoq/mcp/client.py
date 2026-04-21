from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from invoq.llm.ollama import OllamaClient
from invoq.mcp.server import InvoqMCPServer
from invoq.mcp.types import ToolCall, ToolResult


@dataclass
class ChatResult:
    """Result of a chat interaction."""
    response: str
    tool_calls: List[ToolCall]
    tool_results: List[ToolResult]
    raw_response: Dict


class MCPClient:
    """Client that integrates LLM with MCP server for tool execution."""

    def __init__(
        self,
        llm_client: OllamaClient,
        mcp_server: InvoqMCPServer,
        system_prompt: str = "",
    ) -> None:
        self.llm = llm_client
        self.server = mcp_server
        self.system_prompt = system_prompt

    async def chat(self, user_message: str) -> ChatResult:
        """Send a message and handle any tool calls."""
        tools = self.server.get_tools_for_ollama()

        response = await self.llm.generate_with_tools(
            prompt=user_message,
            system_prompt=self.system_prompt,
            tools=tools,
        )

        tool_calls = self.server.parse_ollama_tool_calls(response)
        tool_results: List[ToolResult] = []

        for call in tool_calls:
            result = await self.server.handle_tool_call(call)
            tool_results.append(result)

        text_response = response.get("message", {}).get("content", "")

        # If tool calls were parsed from content, the content IS the tool call JSON
        if tool_calls and not response.get("message", {}).get("tool_calls"):
            text_response = ""

        return ChatResult(
            response=text_response,
            tool_calls=tool_calls,
            tool_results=tool_results,
            raw_response=response,
        )

    async def chat_with_tool_loop(
        self,
        user_message: str,
        max_iterations: int = 5,
    ) -> ChatResult:
        """Chat with automatic tool execution loop.

        Continues calling tools until the model responds without tool calls
        or max_iterations is reached.
        """
        all_tool_calls: List[ToolCall] = []
        all_tool_results: List[ToolResult] = []

        current_message = user_message

        for _ in range(max_iterations):
            result = await self.chat(current_message)

            all_tool_calls.extend(result.tool_calls)
            all_tool_results.extend(result.tool_results)

            if not result.tool_calls:
                return ChatResult(
                    response=result.response,
                    tool_calls=all_tool_calls,
                    tool_results=all_tool_results,
                    raw_response=result.raw_response,
                )

            tool_output = "\n".join(
                f"Tool {r.call_id or 'result'}: {r.output if r.success else r.error}"
                for r in result.tool_results
            )
            current_message = f"Tool results:\n{tool_output}\n\nContinue or provide final answer."

        return ChatResult(
            response="Max tool iterations reached.",
            tool_calls=all_tool_calls,
            tool_results=all_tool_results,
            raw_response={},
        )


__all__ = ["MCPClient", "ChatResult"]
