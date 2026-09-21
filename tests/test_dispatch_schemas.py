import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from invoq.config import Config
from invoq.core.executor import SafeExecutor
from invoq.core.validator import CommandValidator
from invoq.mcp.capabilities import ExecutionBinding, ExecutionMode, ReadOnlyOperation, ToolCapabilities
from invoq.mcp.confirmation import ConfirmationResponse, ConfirmationResult
from invoq.mcp.registry import ToolRegistry, registry
from invoq.mcp.server import InvoqMCPServer
from invoq.mcp.types import ToolCall, ToolParameter, ToolResult


pytestmark = pytest.mark.security


@pytest.fixture
def server(monkeypatch):
    validator = CommandValidator()
    validator.validate = Mock(wraps=validator.validate)
    executor = SafeExecutor(validator, Config(), history=Mock())
    result = SimpleNamespace(
        success=True, stdout="ok", stderr="", failed=False,
        was_blocked=False, commands_blocked=[],
    )
    executor.execute = AsyncMock(return_value=result)
    executor.execute_script = AsyncMock(return_value=result)
    server = InvoqMCPServer(validator=validator, executor=executor, history=Mock())
    approval = ConfirmationResponse(ConfirmationResult.APPROVED)
    server.confirmation_handler.request_confirmation = AsyncMock(return_value=approval)
    server.confirmation_handler.request_script_confirmation = AsyncMock(return_value=approval)
    server.read_handlers = {}
    for operation in ReadOnlyOperation:
        handler = AsyncMock(return_value=ToolResult(None, True, "ok"))
        monkeypatch.setattr(f"invoq.mcp.tools.filesystem.{operation.value}", handler)
        server.read_handlers[operation.value] = handler
    return server


def assert_no_dispatch(server):
    server.validator.validate.assert_not_called()
    server.confirmation_handler.request_confirmation.assert_not_awaited()
    server.confirmation_handler.request_script_confirmation.assert_not_awaited()
    server.executor.execute.assert_not_awaited()
    server.executor.execute_script.assert_not_awaited()
    for handler in server.read_handlers.values():
        handler.assert_not_awaited()


@pytest.mark.parametrize("tool,field,limit", [
    ("execute_command", "command", 1000), ("execute_script", "script", 10000),
])
def test_oversized_execution_input_is_rejected_before_policy_gate(server, tool, field, limit):
    payload = "echo " + "x" * (limit - 4)
    result = asyncio.run(server.handle_tool_call(ToolCall(tool, {field: payload}, "limit")))

    assert not result.success
    assert result.call_id == "limit"
    assert "Invalid arguments" in result.error
    assert field in result.error
    assert str(limit) in result.error
    assert payload not in result.error
    assert_no_dispatch(server)


@pytest.mark.parametrize("max_lines", [0, -1, 1001, True, "10", 1.5, None])
@pytest.mark.parametrize("entry", ["registry", "server"])
def test_read_limits_and_types_are_enforced_before_handler(server, max_lines, entry):
    call = ToolCall("read_file", {"path": "sample.txt", "max_lines": max_lines}, "read")
    dispatch = registry.execute if entry == "registry" else server.handle_tool_call
    result = asyncio.run(dispatch(call))

    assert not result.success
    assert result.call_id == "read"
    assert "Invalid arguments" in result.error
    assert "max_lines" in result.error
    assert_no_dispatch(server)


VALID_ARGUMENTS = [
    ("execute_command", {"command": "echo ok"}),
    ("execute_script", {"script": "echo ok"}),
    ("read_file", {"path": "sample.txt"}),
    ("list_directory", {}),
    ("get_system_info", {}),
]


@pytest.mark.parametrize("tool,arguments", VALID_ARGUMENTS)
def test_extra_arguments_are_rejected_for_every_tool(server, tool, arguments):
    result = asyncio.run(server.handle_tool_call(ToolCall(
        tool, {**arguments, "unexpected": "value"}, "extra",
    )))

    assert not result.success
    assert "Invalid arguments" in result.error
    assert "unexpected" in result.error
    assert_no_dispatch(server)


@pytest.mark.parametrize("tool,arguments", VALID_ARGUMENTS)
@pytest.mark.parametrize("malformed", [None, [], "{}", 1])
def test_non_object_arguments_are_rejected(server, tool, arguments, malformed):
    result = asyncio.run(server.handle_tool_call(ToolCall(tool, malformed)))

    assert not result.success
    assert "Invalid arguments" in result.error
    assert_no_dispatch(server)


@pytest.mark.parametrize("arguments", [
    {"show_hidden": "false"}, {"show_hidden": 1}, {"show_hidden": None}, {"path": 123},
])
def test_directory_schema_is_enforced(server, arguments):
    result = asyncio.run(server.handle_tool_call(ToolCall("list_directory", arguments)))

    assert not result.success
    assert "Invalid arguments" in result.error
    assert_no_dispatch(server)


@pytest.mark.parametrize("tool,field", [("execute_command", "command"),
    ("execute_script", "script"), ("read_file", "path")])
def test_required_fields_are_enforced(server, tool, field):
    result = asyncio.run(server.handle_tool_call(ToolCall(tool, {})))

    assert not result.success
    assert "Invalid arguments" in result.error
    assert field in result.error
    assert_no_dispatch(server)


@pytest.mark.parametrize("tool,field,limit,method", [
    ("execute_command", "command", 1000, "execute"),
    ("execute_script", "script", 10000, "execute_script"),
])
def test_exact_length_limit_reaches_executor_unchanged(server, tool, field, limit, method):
    payload = "echo " + "x" * (limit - 5)
    result = asyncio.run(server.handle_tool_call(ToolCall(tool, {field: payload})))

    assert result.success
    getattr(server.executor, method).assert_awaited_once_with(
        **{field: payload}, working_dir=None, skip_confirmation=True,
    )


@pytest.mark.parametrize("max_lines", [1, 1000])
def test_exact_line_limits_reach_handler(server, max_lines):
    result = asyncio.run(server.handle_tool_call(ToolCall(
        "read_file", {"path": "sample.txt", "max_lines": max_lines},
    )))

    assert result.success
    server.read_handlers["read_file"].assert_awaited_once_with(path="sample.txt", max_lines=max_lines)


@pytest.mark.parametrize("tool,arguments,expected", [
    ("read_file", {"path": "sample.txt"}, {"path": "sample.txt", "max_lines": 100}),
    ("list_directory", {}, {"path": ".", "show_hidden": False}),
    ("get_system_info", {}, {}),
])
def test_validated_defaults_reach_handlers(server, tool, arguments, expected):
    result = asyncio.run(server.handle_tool_call(ToolCall(tool, arguments)))

    assert result.success
    server.read_handlers[tool].assert_awaited_once_with(**expected)


@pytest.mark.parametrize("mode,limit", [(ExecutionMode.COMMAND, 1000), (ExecutionMode.SCRIPT, 10000)])
def test_renamed_execution_tools_inherit_limits(server, mode, limit):
    server.registry = ToolRegistry()
    server.registry.register(
        name="run_alias", description="Bound execution", capabilities=ToolCapabilities(True),
        validator_hook=ExecutionBinding(mode, "payload", "directory"),
        parameters=[ToolParameter("payload", "string", "Content"),
                    ToolParameter("directory", "string", "Directory", required=False)],
    )
    result = asyncio.run(server.handle_tool_call(ToolCall(
        "run_alias", {"payload": "echo " + "x" * limit},
    )))

    assert not result.success
    assert "Invalid arguments" in result.error
    assert "payload" in result.error
    assert_no_dispatch(server)


def test_renamed_read_tools_inherit_limits(server):
    server.registry = ToolRegistry()
    server.registry.register(
        name="read_alias", description="Read", capabilities=ToolCapabilities(False),
        handler=ReadOnlyOperation.READ_FILE,
    )
    result = asyncio.run(server.handle_tool_call(ToolCall(
        "read_alias", {"path": "sample.txt", "max_lines": 0},
    )))

    assert not result.success
    assert "Invalid arguments" in result.error
    assert_no_dispatch(server)


def test_advertised_schemas_include_enforced_limits():
    schemas = {tool["function"]["name"]: tool["function"]["parameters"]
               for tool in registry.to_ollama_tools()}

    assert schemas["execute_command"]["properties"]["command"]["maxLength"] == 1000
    assert schemas["execute_script"]["properties"]["script"]["maxLength"] == 10000
    assert schemas["read_file"]["properties"]["max_lines"]["minimum"] == 1
    assert schemas["read_file"]["properties"]["max_lines"]["maximum"] == 1000
    assert all(schema["additionalProperties"] is False for schema in schemas.values())


@pytest.mark.parametrize("renamed", [False, True])
def test_edited_commands_cannot_bypass_length_limit(server, renamed):
    name, parameter = "execute_command", "command"
    if renamed:
        name, parameter = "run_alias", "payload"
        server.registry = ToolRegistry()
        server.registry.register(
            name=name, description="Command", capabilities=ToolCapabilities(True),
            validator_hook=ExecutionBinding(ExecutionMode.COMMAND, parameter, None),
            parameters=[ToolParameter(parameter, "string", "Content")],
        )
    server.confirmation_handler.request_confirmation.return_value = ConfirmationResponse(
        ConfirmationResult.EDITED, "echo " + "x" * 996,
    )

    result = asyncio.run(server.handle_tool_call(ToolCall(name, {parameter: "echo ok"}, "edit")))

    assert not result.success
    assert result.call_id == "edit"
    assert "Invalid arguments" in result.error
    assert parameter in result.error
    server.executor.execute.assert_not_awaited()


@pytest.mark.parametrize("mode,limit", [(ExecutionMode.COMMAND, 1000), (ExecutionMode.SCRIPT, 10000)])
def test_binding_without_directory_preserves_limits_and_rejects_extra_fields(server, mode, limit):
    server.registry = ToolRegistry()
    server.registry.register(
        name="run", description="Command", capabilities=ToolCapabilities(True),
        validator_hook=ExecutionBinding(mode, "payload", None),
        parameters=[ToolParameter("payload", "string", "Content")],
    )
    schema = server.registry.to_ollama_tools()[0]["function"]["parameters"]
    assert schema["properties"]["payload"]["maxLength"] == limit
    assert "working_dir" not in schema["properties"]
    result = asyncio.run(server.handle_tool_call(ToolCall(
        "run", {"payload": "echo ok", "working_dir": "/tmp"},
    )))

    assert not result.success
    assert "Invalid arguments" in result.error
    assert_no_dispatch(server)
