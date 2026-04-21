"""MCP (Model Context Protocol) server for invoq."""

from .client import ChatResult, MCPClient
from .registry import ToolRegistry, registry
from .schemas import (
    DirectoryEntry,
    DirectoryListing,
    CommandOutput,
    ExecuteCommandInput,
    ExecuteScriptInput,
    FileContent,
    ListDirectoryInput,
    ReadFileInput,
    SystemInfo,
)
from .server import InvoqMCPServer, server
from .types import ToolCall, ToolDefinition, ToolParameter, ToolResult

__all__ = [
    "ToolDefinition",
    "ToolCall",
    "ToolResult",
    "ToolParameter",
    "ToolRegistry",
    "registry",
    "InvoqMCPServer",
    "server",
    "MCPClient",
    "ChatResult",
    "ExecuteCommandInput",
    "ExecuteScriptInput",
    "ReadFileInput",
    "ListDirectoryInput",
    "SystemInfo",
    "CommandOutput",
    "FileContent",
    "DirectoryEntry",
    "DirectoryListing",
]
