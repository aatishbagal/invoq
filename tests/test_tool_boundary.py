import asyncio
import subprocess
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from invoq.core.executor import SafeExecutor
from invoq.mcp.registry import ToolRegistry, registry
from invoq.mcp.server import InvoqMCPServer
from invoq.mcp.types import ToolCall, ToolResult


@pytest.mark.parametrize("handler_style", ["direct", "decorator"])
def test_undeclared_subprocess_handler_is_rejected(monkeypatch, handler_style):
    run = Mock()
    monkeypatch.setattr(subprocess, "run", run)

    async def hidden_process():
        subprocess.run(["echo", "unexpected"], check=True)
        return ToolResult(None, True, "unexpected")

    reg = ToolRegistry()
    with pytest.raises(ValueError, match="capabilit"):
        if handler_style == "direct":
            reg.register(name="hidden", description="Hidden subprocess", handler=hidden_process)
        else:
            reg.register(name="hidden", description="Hidden subprocess")(hidden_process)

    assert reg.get("hidden") is None
    run.assert_not_called()


@pytest.mark.parametrize("tool,argument,method", [
    ("execute_command", "command", "execute"),
    ("execute_script", "script", "execute_script"),
])
def test_registry_cannot_execute_process_tools_directly(monkeypatch, tool, argument, method):
    execute = AsyncMock(return_value=SimpleNamespace(
        success=True, stdout="unexpected", stderr="", failed=False,
        was_blocked=False, was_cancelled=False, commands_blocked=[],
    ))
    monkeypatch.setattr(SafeExecutor, method, execute)

    result = asyncio.run(registry.execute(ToolCall(tool, {argument: "echo harmless"}, "call")))

    assert not result.success
    assert "server" in result.error.lower()
    assert result.call_id == "call"
    execute.assert_not_awaited()


@pytest.mark.parametrize("tool,argument", [("execute_command", "command"), ("execute_script", "script")])
def test_shell_convenience_functions_use_server_gate(monkeypatch, tool, argument):
    from invoq.mcp.tools import shell

    expected = ToolResult(None, False, "", "Denied by server")
    gate = AsyncMock(return_value=expected)
    monkeypatch.setattr(InvoqMCPServer, "handle_tool_call", gate)
    execute = AsyncMock()
    monkeypatch.setattr(SafeExecutor, "execute", execute)
    monkeypatch.setattr(SafeExecutor, "execute_script", execute)

    result = asyncio.run(getattr(shell, tool)(**{argument: "echo ok"}, working_dir="/tmp"))

    assert result is expected
    gate.assert_awaited_once_with(ToolCall(tool, {argument: "echo ok", "working_dir": "/tmp"}))
    execute.assert_not_awaited()
