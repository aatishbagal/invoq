import asyncio
from dataclasses import FrozenInstanceError
from unittest.mock import Mock

import pytest

from invoq.mcp.capabilities import ExecutionBinding, ExecutionMode, ReadOnlyOperation, ToolCapabilities
from invoq.mcp.registry import ToolRegistry, registry
from invoq.mcp.types import ToolCall, ToolParameter, ToolResult


pytestmark = pytest.mark.security


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



@pytest.mark.parametrize("declared", [False, True])
def test_arbitrary_python_handlers_are_refused_even_with_capabilities(declared):
    process = Mock()

    async def disguised():
        process()
        return ToolResult(None, True, "unapproved")

    kwargs = {}
    if declared:
        kwargs["validator_hook"] = ExecutionBinding(ExecutionMode.COMMAND, "command", None)
    reg = ToolRegistry()
    with pytest.raises(ValueError, match="Python handlers"):
        reg.register(
            name="disguised", description="Attempts to bypass the gate",
            parameters=[ToolParameter("command", "string", "Command")],
            capabilities=ToolCapabilities(subprocess=declared), handler=disguised, **kwargs,
        )
    assert reg.get("disguised") is None
    process.assert_not_called()



def test_subprocess_declaration_requires_validator_hook():
    with pytest.raises(ValueError, match="validator hook"):
        ToolRegistry().register(name="missing", description="Missing hook", capabilities=ToolCapabilities(True))



def test_validator_hook_cannot_be_an_arbitrary_callback():
    callback = Mock()
    with pytest.raises(ValueError, match="validator hook"):
        ToolRegistry().register(
            name="callback", description="Invalid hook", capabilities=ToolCapabilities(True),
            validator_hook=callback,
        )
    callback.assert_not_called()



def test_validator_hook_requires_declared_subprocess_capability():
    with pytest.raises(ValueError, match="requires subprocess capability"):
        ToolRegistry().register(
            name="undeclared", description="Missing capability", capabilities=ToolCapabilities(False),
            handler=ReadOnlyOperation.GET_SYSTEM_INFO,
            validator_hook=ExecutionBinding(ExecutionMode.COMMAND, "command", None),
        )



@pytest.mark.parametrize("parameters", [[], [ToolParameter("payload", "integer", "Wrong type")],
    [ToolParameter("payload", "string", "Optional", required=False)]])
def test_validator_hook_requires_declared_command_parameter(parameters):
    with pytest.raises(ValueError, match="required string parameter"):
        ToolRegistry().register(
            name="invalid", description="Invalid schema", parameters=parameters,
            capabilities=ToolCapabilities(True),
            validator_hook=ExecutionBinding(ExecutionMode.COMMAND, "payload", None),
        )



def test_duplicate_registration_cannot_replace_capabilities():
    reg = ToolRegistry()
    original = register_execution(reg, "run", ExecutionMode.COMMAND)
    with pytest.raises(ValueError, match="already registered"):
        reg.register(
            name="run", description="Replace execution with read-only", capabilities=ToolCapabilities(False),
            handler=ReadOnlyOperation.GET_SYSTEM_INFO,
        )
    assert reg.get("run") is original



def test_registered_capabilities_and_hooks_are_immutable():
    tool = register_execution(ToolRegistry(), "run", ExecutionMode.COMMAND)
    with pytest.raises(FrozenInstanceError):
        tool.definition.capabilities.subprocess = False
    with pytest.raises(FrozenInstanceError):
        tool.definition.capabilities = ToolCapabilities(False)
    with pytest.raises(FrozenInstanceError):
        tool.validator_hook = None
    with pytest.raises(FrozenInstanceError):
        tool.validator_hook.mode = ExecutionMode.SCRIPT



@pytest.mark.parametrize("mode", list(ExecutionMode))
def test_execution_declarations_cannot_use_registry_dispatch(mode):
    reg = ToolRegistry()
    register_execution(reg, "unapproved", mode)
    result = asyncio.run(reg.execute(ToolCall("unapproved", {"payload": "echo ok"}, "id")))
    assert not result.success
    assert "server-owned" in result.error
    assert result.call_id == "id"



def test_all_builtin_tools_declare_capabilities():
    declarations = {tool.name: tool.capabilities.subprocess for tool in registry.list_tools()}
    assert declarations == {
        "execute_command": True, "execute_script": True,
        "read_file": False, "list_directory": False, "get_system_info": False,
    }

