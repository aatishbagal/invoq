import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from invoq.config import Config
from invoq.core.executor import ConfirmationChoice, SafeExecutor
from invoq.core.validator import CommandValidator


pytestmark = pytest.mark.security


@pytest.mark.parametrize("script", [
    "echo ok\n> /dev/sda", "echo ok\n$(whoami)", "echo 'unterminated",
    "#!/tmp/custom-interpreter\necho ok", "echo ok <<EOF\npayload\nEOF",
])
def test_script_validation_cannot_drop_unsupported_constructs(script):
    executor = SafeExecutor(CommandValidator(), Config(), history=Mock())
    executor._run_subprocess = AsyncMock(return_value=(0, "", "", 0, False))

    result = asyncio.run(executor.execute_script(script, skip_confirmation=True))

    assert not result.success
    assert result.commands_blocked
    executor._run_subprocess.assert_not_awaited()


@pytest.mark.parametrize("method,argument", [("execute", "command"), ("execute_script", "script")])
@pytest.mark.parametrize("command", [">/tmp/invoq-output", "echo payload >/tmp/invoq-output"])
def test_executor_requires_approval_for_redirects(method, argument, command):
    executor = SafeExecutor(CommandValidator(), Config(), history=Mock())
    executor._prompt_confirmation = Mock(return_value=ConfirmationChoice.NO)
    executor._run_subprocess = AsyncMock(return_value=(0, "", "", 0, False))

    result = asyncio.run(getattr(executor, method)(**{argument: command}))

    assert result.was_cancelled
    assert not result.success
    executor._prompt_confirmation.assert_called_once()
    executor._run_subprocess.assert_not_awaited()
