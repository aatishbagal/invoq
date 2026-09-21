import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from invoq.config import Config
from invoq.core.executor import ExecutionResult, SafeExecutor, ScriptExecutionResult
from invoq.core.validator import CommandValidator
from invoq.mcp.capabilities import ExecutionBinding, ExecutionMode, ReadOnlyOperation, ToolCapabilities
from invoq.mcp.confirmation import ConfirmationHandler, ConfirmationResponse, ConfirmationResult, console
from invoq.mcp.registry import ToolRegistry
from invoq.mcp.server import InvoqMCPServer
from invoq.mcp.types import ToolCall, ToolParameter


def register_execution(reg, name, mode):
    return reg.register(
        name=name, description="Test execution declaration",
        capabilities=ToolCapabilities(subprocess=True),
        validator_hook=ExecutionBinding(mode, "payload", "directory"),
        parameters=[
            ToolParameter("payload", "string", "Command or script"),
            ToolParameter("directory", "string", "Working directory", required=False),
        ],
    )


@pytest.fixture
def server(monkeypatch):
    validator = CommandValidator()
    executor = SafeExecutor(validator, Config(), history=Mock())
    executor.execute = AsyncMock(return_value=ExecutionResult(True, 0, "ok", "", "echo ok", 0))
    executor.execute_script = AsyncMock(return_value=ScriptExecutionResult(True, 0, "ok", "", "echo ok", "", 0))
    monkeypatch.setattr(console, "print", Mock())
    return InvoqMCPServer(
        tool_registry=ToolRegistry(), validator=validator, executor=executor, history=Mock(),
    )


@pytest.mark.parametrize("mode", list(ExecutionMode))
@pytest.mark.parametrize("approval", ["y", "n"])
def test_every_execution_capability_uses_server_gate(server, monkeypatch, mode, approval):
    register_execution(server.registry, "new_execution_tool", mode)
    prompt = Mock(return_value=approval)
    monkeypatch.setattr(console, "input", prompt)
    validate = Mock(wraps=server.validator.validate)
    monkeypatch.setattr(server.validator, "validate", validate)

    result = asyncio.run(server.handle_tool_call(ToolCall(
        "new_execution_tool", {"payload": "echo ok", "directory": "/tmp"}, "call-1",
    )))

    prompt.assert_called_once()
    validate.assert_any_call("echo ok")
    assert result.call_id == "call-1"
    assert result.success is (approval == "y")
    execute = server.executor.execute if mode == ExecutionMode.COMMAND else server.executor.execute_script
    if approval == "y":
        execute.assert_awaited_once_with(**{mode.value: "echo ok"}, working_dir="/tmp", skip_confirmation=True)
    else:
        server.executor.execute.assert_not_awaited()
        server.executor.execute_script.assert_not_awaited()


@pytest.mark.parametrize("mode", list(ExecutionMode))
def test_blocked_execution_is_rejected_before_prompt(server, monkeypatch, mode):
    register_execution(server.registry, "new_execution_tool", mode)
    prompt = Mock(return_value="y")
    monkeypatch.setattr(console, "input", prompt)

    result = asyncio.run(server.handle_tool_call(ToolCall(
        "new_execution_tool", {"payload": "echo ok\n> /dev/sda"},
    )))

    assert not result.success
    assert "BLOCKED" in result.error
    prompt.assert_not_called()
    server.executor.execute.assert_not_awaited()
    server.executor.execute_script.assert_not_awaited()


@pytest.mark.parametrize("mode", list(ExecutionMode))
def test_redirect_only_execution_requires_confirmation_without_remediation(server, monkeypatch, mode):
    server.config.security.remediation_mode = False
    register_execution(server.registry, "write_output", mode)
    prompt = Mock(return_value="n")
    monkeypatch.setattr(console, "input", prompt)

    result = asyncio.run(server.handle_tool_call(ToolCall("write_output", {"payload": ">/tmp/output"})))

    prompt.assert_called_once()
    assert not result.success
    server.executor.execute.assert_not_awaited()
    server.executor.execute_script.assert_not_awaited()


@pytest.mark.parametrize("mode", list(ExecutionMode))
@pytest.mark.parametrize("arguments", [None, [], {}, {"payload": 7}, {"payload": "echo ok", "directory": 7}])
def test_invalid_execution_arguments_fail_closed(server, monkeypatch, mode, arguments):
    register_execution(server.registry, "run", mode)
    prompt = Mock()
    monkeypatch.setattr(console, "input", prompt)

    result = asyncio.run(server.handle_tool_call(ToolCall("run", arguments)))

    assert not result.success
    assert "Invalid arguments" in result.error
    prompt.assert_not_called()
    server.executor.execute.assert_not_awaited()
    server.executor.execute_script.assert_not_awaited()


@pytest.mark.parametrize("mode", list(ExecutionMode))
def test_invalid_confirmation_response_cannot_authorize_execution(server, monkeypatch, mode):
    register_execution(server.registry, "run", mode)
    method = "request_confirmation" if mode == ExecutionMode.COMMAND else "request_script_confirmation"
    monkeypatch.setattr(server.confirmation_handler, method, AsyncMock(
        return_value=ConfirmationResponse("unexpected"),
    ))

    result = asyncio.run(server.handle_tool_call(ToolCall("run", {"payload": "echo ok"})))

    assert not result.success
    server.executor.execute.assert_not_awaited()
    server.executor.execute_script.assert_not_awaited()


def test_edited_commands_are_revalidated_by_server(server, monkeypatch):
    register_execution(server.registry, "run", ExecutionMode.COMMAND)
    monkeypatch.setattr(server.confirmation_handler, "request_confirmation", AsyncMock(
        return_value=ConfirmationResponse(ConfirmationResult.EDITED, "find /tmp -delete"),
    ))

    result = asyncio.run(server.handle_tool_call(ToolCall("run", {"payload": "echo ok"})))

    assert not result.success
    assert "BLOCKED" in result.error
    server.executor.execute.assert_not_awaited()


def test_server_and_executor_share_validator_when_executor_is_injected(server):
    reconstructed = InvoqMCPServer(executor=server.executor, history=Mock())
    assert reconstructed.validator is server.executor.validator
    assert reconstructed.confirmation_handler.validator is reconstructed.validator


def test_mismatched_validators_are_refused(server):
    with pytest.raises(ValueError, match="same validator"):
        InvoqMCPServer(validator=CommandValidator(), executor=server.executor, history=Mock())
    with pytest.raises(ValueError, match="same validator"):
        InvoqMCPServer(
            validator=server.validator, executor=server.executor, history=Mock(),
            confirmation_handler=ConfirmationHandler(CommandValidator()),
        )


@pytest.mark.parametrize("operation", list(ReadOnlyOperation))
def test_reviewed_read_only_operations_do_not_request_execution_approval(server, monkeypatch, tmp_path, operation):
    file = tmp_path / "sample.txt"
    file.write_text("sample")
    arguments = {}
    if operation == ReadOnlyOperation.READ_FILE:
        arguments["path"] = str(file)
    elif operation == ReadOnlyOperation.LIST_DIRECTORY:
        arguments["path"] = str(tmp_path)
    server.registry.register(
        name="read_only_alias", description="Reviewed operation",
        capabilities=ToolCapabilities(False), handler=operation,
    )
    prompt = Mock()
    monkeypatch.setattr(console, "input", prompt)

    result = asyncio.run(server.handle_tool_call(ToolCall("read_only_alias", arguments, "read-only")))

    assert result.success
    assert result.call_id == "read-only"
    prompt.assert_not_called()
    server.executor.execute.assert_not_awaited()
    server.executor.execute_script.assert_not_awaited()


@pytest.mark.parametrize("edited", [None, "", "   ", 7, "echo edited"])
def test_edited_execution_requires_valid_text_and_uses_exact_approved_content(server, monkeypatch, edited):
    register_execution(server.registry, "run", ExecutionMode.COMMAND)
    monkeypatch.setattr(server.confirmation_handler, "request_confirmation", AsyncMock(
        return_value=ConfirmationResponse(ConfirmationResult.EDITED, edited),
    ))

    result = asyncio.run(server.handle_tool_call(ToolCall("run", {"payload": "echo original"})))

    if edited == "echo edited":
        assert result.success
        server.executor.execute.assert_awaited_once_with(
            command=edited, working_dir=None, skip_confirmation=True,
        )
    else:
        assert not result.success
        server.executor.execute.assert_not_awaited()


def test_unregistered_builtin_name_cannot_bypass_registry():
    validator = CommandValidator()
    executor = SafeExecutor(validator, Config(), history=Mock())
    executor.execute = AsyncMock(return_value=SimpleNamespace(
        success=True, stdout="unexpected", stderr="", failed=False, was_blocked=False,
    ))
    confirmation = Mock()
    confirmation.validator = validator
    confirmation.request_confirmation = AsyncMock(return_value=ConfirmationResponse(
        ConfirmationResult.APPROVED,
    ))
    server = InvoqMCPServer(
        tool_registry=ToolRegistry(), validator=validator, executor=executor,
        history=Mock(), confirmation_handler=confirmation,
    )

    result = asyncio.run(server.handle_tool_call(ToolCall("execute_command", {"command": "echo hi"})))

    assert not result.success
    assert "Unknown tool" in result.error
    executor.execute.assert_not_awaited()
    confirmation.request_confirmation.assert_not_awaited()

