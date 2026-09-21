from __future__ import annotations

import asyncio
import logging
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from invoq.config import Config
from invoq.core.executor import SafeExecutor
from invoq.core.tiers import CommandTier
from invoq.core.validator import CommandValidator, ValidationResult
from invoq.mcp.confirmation import ConfirmationHandler, console
from invoq.mcp.server import InvoqMCPServer
from invoq.mcp.types import ToolCall


@pytest.fixture
def server(monkeypatch):
    config = Config()
    validator = CommandValidator()
    history = Mock()
    executor = SafeExecutor(validator, config, history=history)
    executor.execute = AsyncMock()
    executor.execute_script = AsyncMock()
    monkeypatch.setattr(console, "print", Mock())
    return InvoqMCPServer(
        validator=validator,
        executor=executor,
        history=history,
        confirmation_handler=ConfirmationHandler(validator),
    )


@pytest.mark.parametrize("tool,argument", [
    ("execute_command", "command"),
    ("execute_script", "script"),
])
@pytest.mark.parametrize("command", [
    "echo hello",
    "echo first\necho second",
    "awk 'BEGIN { system(\"rm -rf /tmp/x\") }'",
    r'find /tmp -exec r"m" -rf {} \;',
    "echo payload > /tmp/file",
    "find /tmp -delete",
    "sed -i 's/a/b/' file",
])
def test_safe_calls_require_manual_approval(server, monkeypatch, tool, argument, command):
    monkeypatch.setattr(server.validator, "validate", Mock(return_value=ValidationResult(
        allowed=True, tier=CommandTier.SAFE, reason="Simulated SAFE classification",
        commands_found=["echo"],
    )))
    validation = server.validator.validate(command)
    assert validation.allowed
    assert validation.tier == CommandTier.SAFE
    prompt = Mock(return_value="n")
    monkeypatch.setattr(console, "input", prompt)

    result = asyncio.run(server.handle_tool_call(ToolCall(tool, {argument: command})))

    prompt.assert_called_once()
    assert not result.success
    assert "cancelled" in result.error.lower()
    server.executor.execute.assert_not_awaited()
    server.executor.execute_script.assert_not_awaited()


@pytest.mark.parametrize("tool,argument", [
    ("execute_command", "command"),
    ("execute_script", "script"),
])
def test_approval_precedes_each_execution(server, monkeypatch, tool, argument):
    execute = getattr(server.executor, "execute" if argument == "command" else tool)
    execute.return_value = SimpleNamespace(
        success=True, stdout="hello", stderr="", failed=False,
        was_blocked=False, commands_blocked=[],
    )

    def approve(_prompt):
        assert execute.await_count == prompt.call_count - 1
        return "y"

    prompt = Mock(side_effect=approve)
    monkeypatch.setattr(console, "input", prompt)
    call = ToolCall(tool, {argument: "echo hello", "working_dir": "/tmp"})

    for _ in range(2):
        result = asyncio.run(server.handle_tool_call(call))
        assert result.success

    assert prompt.call_count == 2
    assert execute.await_count == 2
    execute.assert_awaited_with(
        **{argument: "echo hello"}, working_dir="/tmp", skip_confirmation=True,
    )


@pytest.mark.parametrize("tool,argument", [
    ("execute_command", "command"),
    ("execute_script", "script"),
])
def test_unavailable_approval_never_executes(server, monkeypatch, tool, argument):
    prompt = Mock(side_effect=EOFError)
    monkeypatch.setattr(console, "input", prompt)

    with pytest.raises(EOFError):
        asyncio.run(server.handle_tool_call(ToolCall(tool, {argument: "echo hello"})))

    prompt.assert_called_once()
    server.executor.execute.assert_not_awaited()
    server.executor.execute_script.assert_not_awaited()


@pytest.mark.parametrize("tool,argument", [
    ("execute_command", "command"),
    ("execute_script", "script"),
])
def test_blocked_calls_remain_blocked(server, monkeypatch, tool, argument):
    prompt = Mock(return_value="y")
    monkeypatch.setattr(console, "input", prompt)

    result = asyncio.run(server.handle_tool_call(
        ToolCall(tool, {argument: "rm -rf /tmp/invoq-blocked"})
    ))

    assert not result.success
    prompt.assert_not_called()
    server.executor.execute.assert_not_awaited()
    server.executor.execute_script.assert_not_awaited()


def test_default_server_loads_remediation_mode(monkeypatch, caplog):
    config = Config()
    loader = Mock(return_value=config)
    monkeypatch.setattr(import_module("invoq.mcp.server"), "load_config", loader)

    with caplog.at_level(logging.WARNING):
        InvoqMCPServer(history=Mock())

    loader.assert_called_once()
    assert "Running in remediation mode: all command execution requires manual approval." in caplog.text


@pytest.mark.parametrize("enabled", [True, False])
def test_injected_executor_controls_startup_warning(server, caplog, enabled):
    server.executor.config.security.remediation_mode = enabled
    caplog.clear()

    with caplog.at_level(logging.WARNING):
        InvoqMCPServer(executor=server.executor, history=Mock())

    warning = "Running in remediation mode: all command execution requires manual approval."
    assert (warning in caplog.text) is enabled


@pytest.mark.parametrize("tool,argument", [
    ("execute_command", "command"),
    ("execute_script", "script"),
])
def test_disabled_remediation_preserves_safe_auto_approval(server, monkeypatch, tool, argument):
    server.config.security.remediation_mode = False
    prompt = Mock()
    monkeypatch.setattr(console, "input", prompt)

    asyncio.run(server.handle_tool_call(ToolCall(tool, {argument: "echo hello"})))

    prompt.assert_not_called()
    execute = getattr(server.executor, "execute" if argument == "command" else tool)
    execute.assert_awaited_once()


@pytest.mark.parametrize("tool,argument", [
    ("execute_command", "command"),
    ("execute_script", "script"),
])
def test_tool_arguments_cannot_disable_gate(server, monkeypatch, tool, argument):
    prompt = Mock(return_value="n")
    monkeypatch.setattr(console, "input", prompt)
    arguments = {
        argument: "echo hello",
        "remediation_mode": False,
        "force_confirmation": False,
        "skip_confirmation": True,
    }

    result = asyncio.run(server.handle_tool_call(ToolCall(tool, arguments)))

    prompt.assert_not_called()
    assert not result.success
    assert "Invalid arguments" in result.error
    for field in ("remediation_mode", "force_confirmation", "skip_confirmation"):
        assert field in result.error
    server.executor.execute.assert_not_awaited()
    server.executor.execute_script.assert_not_awaited()
