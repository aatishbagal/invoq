from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from invoq.mcp.registry import ToolRegistry
from invoq.mcp.server import InvoqMCPServer
from invoq.mcp.types import ToolCall, ToolParameter, ToolResult


def _run(coro):
    return asyncio.run(coro)


class TestToolRegistry:
    def test_register_tool(self) -> None:
        reg = ToolRegistry()

        @reg.register(
            name="test_tool",
            description="A test tool",
            parameters=[ToolParameter("arg", "string", "An argument")],
        )
        async def test_tool(arg: str) -> ToolResult:
            return ToolResult(call_id=None, success=True, output=arg)

        assert "test_tool" in [t.name for t in reg.list_tools()]

    def test_list_tools(self) -> None:
        reg = ToolRegistry()

        @reg.register(name="tool1", description="Tool 1")
        async def tool1() -> ToolResult:
            return ToolResult(call_id=None, success=True, output="1")

        @reg.register(name="tool2", description="Tool 2")
        async def tool2() -> ToolResult:
            return ToolResult(call_id=None, success=True, output="2")

        tools = reg.list_tools()
        assert len(tools) == 2

    def test_execute_tool(self) -> None:
        reg = ToolRegistry()

        @reg.register(
            name="echo",
            description="Echo",
            parameters=[ToolParameter("msg", "string", "Message")],
        )
        async def echo(msg: str) -> ToolResult:
            return ToolResult(call_id=None, success=True, output=msg)

        result = _run(reg.execute(ToolCall("echo", {"msg": "hello"})))
        assert result.success
        assert result.output == "hello"

    def test_execute_unknown_tool(self) -> None:
        reg = ToolRegistry()
        result = _run(reg.execute(ToolCall("unknown", {})))
        assert not result.success
        assert "Unknown tool" in result.error

    def test_execute_invalid_arguments(self) -> None:
        reg = ToolRegistry()

        @reg.register(
            name="needs_arg",
            description="Needs arg",
            parameters=[ToolParameter("arg", "string", "An argument")],
        )
        async def needs_arg(arg: str) -> ToolResult:
            return ToolResult(call_id=None, success=True, output=arg)

        result = _run(reg.execute(ToolCall("needs_arg", {})))
        assert not result.success
        assert "Invalid arguments" in result.error

    def test_to_ollama_tools_format(self) -> None:
        reg = ToolRegistry()

        @reg.register(
            name="sample",
            description="Sample tool",
            parameters=[
                ToolParameter("a", "string", "A param"),
                ToolParameter("b", "integer", "B param", required=False),
            ],
        )
        async def sample(a: str, b: int = 0) -> ToolResult:
            return ToolResult(call_id=None, success=True, output="")

        tools = reg.to_ollama_tools()
        assert len(tools) == 1
        tool = tools[0]
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "sample"
        assert "a" in tool["function"]["parameters"]["properties"]
        assert "b" in tool["function"]["parameters"]["properties"]
        assert tool["function"]["parameters"]["required"] == ["a"]


class TestMCPServer:
    def test_get_tools(self) -> None:
        server = InvoqMCPServer()
        tools = server.get_tools()

        tool_names = [t.name for t in tools]
        assert "execute_command" in tool_names
        assert "read_file" in tool_names
        assert "list_directory" in tool_names
        assert "get_system_info" in tool_names

    def test_get_tools_for_ollama(self) -> None:
        server = InvoqMCPServer()
        tools = server.get_tools_for_ollama()

        assert isinstance(tools, list)
        assert len(tools) > 0

        tool = tools[0]
        assert "type" in tool
        assert tool["type"] == "function"
        assert "function" in tool
        assert "name" in tool["function"]

    def test_parse_ollama_tool_calls(self) -> None:
        server = InvoqMCPServer()

        ollama_response = {
            "message": {
                "tool_calls": [
                    {
                        "id": "call_123",
                        "function": {
                            "name": "read_file",
                            "arguments": {"path": "/tmp/test.txt"},
                        },
                    }
                ]
            }
        }

        calls = server.parse_ollama_tool_calls(ollama_response)
        assert len(calls) == 1
        assert calls[0].name == "read_file"
        assert calls[0].arguments == {"path": "/tmp/test.txt"}
        assert calls[0].call_id == "call_123"

    def test_parse_ollama_tool_calls_empty(self) -> None:
        server = InvoqMCPServer()
        calls = server.parse_ollama_tool_calls({"message": {}})
        assert calls == []


class TestFileSystemTools:
    def test_read_file(self) -> None:
        from invoq.mcp.tools.filesystem import read_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("line1\nline2\nline3")
            path = f.name

        try:
            result = _run(read_file(path))
            assert result.success
            assert "line1" in result.output
            assert "line2" in result.output
        finally:
            Path(path).unlink()

    def test_read_file_not_found(self) -> None:
        from invoq.mcp.tools.filesystem import read_file

        result = _run(read_file("/nonexistent/file.txt"))
        assert not result.success
        assert "not found" in result.error.lower()

    def test_read_file_max_lines(self) -> None:
        from invoq.mcp.tools.filesystem import read_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("\n".join(f"line{i}" for i in range(20)))
            path = f.name

        try:
            result = _run(read_file(path, max_lines=5))
            assert result.success
            assert "truncated" in result.output
        finally:
            Path(path).unlink()

    def test_list_directory(self) -> None:
        from invoq.mcp.tools.filesystem import list_directory

        result = _run(list_directory("."))
        assert result.success
        assert "Directory:" in result.output

    def test_list_directory_not_found(self) -> None:
        from invoq.mcp.tools.filesystem import list_directory

        result = _run(list_directory("/nonexistent/dir/xyz"))
        assert not result.success

    def test_get_system_info(self) -> None:
        from invoq.mcp.tools.filesystem import get_system_info

        result = _run(get_system_info())
        assert result.success
        assert "os:" in result.output.lower()
        assert "shell:" in result.output.lower()
