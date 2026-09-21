import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from invoq.config import Config
from invoq.core.executor import ConfirmationChoice, SafeExecutor
from invoq.core.validator import CommandValidator


@pytest.fixture
def executor():
    executor = SafeExecutor(CommandValidator(), Config(), history=Mock())
    executor._run_subprocess = AsyncMock(return_value=(0, "", "", 0, False))
    executor._prompt_confirmation = Mock(return_value=ConfirmationChoice.YES)
    return executor


@pytest.mark.parametrize("script", [
    "echo one\necho two",
    "echo one; echo two",
    "echo one || echo two",
    "echo one | cat",
    "echo one & echo two",
    "#!/bin/bash\necho one",
    "echo one # comment",
    "echo one \\\n&& echo two",
    "echo 'one\ntwo'",
    "if true; then echo one; fi",
    "while false; do echo one; done",
    "until true; do echo one; done",
    "for x in one; do echo one; done",
    "case one in one) echo one;; esac",
    "f() { echo one; }; f",
    "function f { echo one; }; f",
    "ls && $(rm -rf /tmp/x)",
    "echo one && echo $(whoami)",
    "echo one && echo `whoami`",
    "echo one && cat <(echo two)",
    "echo one && echo two >(cat)",
    "cat <<EOF\none\nEOF",
    "cat <<<one",
    "CMD=ls && $CMD",
    "echo one && ${CMD}",
    "echo one && echo $HOME",
    "echo one && (echo two)",
    "echo one && { echo two; }",
    "echo one && echo *.txt",
    "echo one &&",
    "&& echo one",
    "echo one && && echo two",
    "echo 'unterminated",
    "",
    "   ",
])
@pytest.mark.parametrize("skip_confirmation", [False, True])
def test_rejects_non_flat_scripts_before_execution(executor, script, skip_confirmation):
    result = asyncio.run(executor.execute_script(
        script, skip_confirmation=skip_confirmation,
    ))

    assert not result.success
    assert result.commands_blocked
    assert result.script_path == ""
    executor._prompt_confirmation.assert_not_called()
    executor._run_subprocess.assert_not_awaited()


@pytest.mark.parametrize("keyword", [
    "if", "then", "else", "elif", "fi", "while", "until", "do", "done",
    "for", "in", "case", "esac", "select", "function", "time", "coproc", "!",
])
def test_extensions_cannot_allow_control_syntax(executor, keyword):
    executor.validator.add_extension_commands({keyword})

    result = asyncio.run(executor.execute_script(
        f"echo one && {keyword} true", skip_confirmation=True,
    ))

    assert not result.success
    assert result.commands_blocked
    executor._run_subprocess.assert_not_awaited()


def test_validates_each_command_before_running_chain(executor):
    executor.validator.validate = Mock(wraps=executor.validator.validate)

    result = asyncio.run(executor.execute_script("echo one && ls -la"))

    assert result.success
    assert [call.args[0] for call in executor.validator.validate.call_args_list] == [
        "echo one", "ls -la",
    ]
    executor._run_subprocess.assert_awaited_once_with(
        "echo one && ls -la", None, None, is_script=False,
    )


def test_disallowed_later_command_prevents_entire_chain(executor):
    result = asyncio.run(executor.execute_script("echo one && rm -rf /tmp/x"))

    assert not result.success
    assert result.commands_blocked
    executor._prompt_confirmation.assert_not_called()
    executor._run_subprocess.assert_not_awaited()


@pytest.mark.parametrize("script", [
    "echo one && echo two",
    "echo 'one && two' && echo three",
    r"echo one\&\&two && echo three",
    "echo 'if while for case function'",
    "echo '$(whoami) `whoami` $HOME <(echo one)'",
    "echo '#literal'",
])
def test_accepts_literal_commands(executor, script):
    result = asyncio.run(executor.execute_script(script))

    assert result.success
    executor._prompt_confirmation.assert_not_called()
    executor._run_subprocess.assert_awaited_once_with(
        script, None, None, is_script=False,
    )


def test_confirmation_covers_the_entire_chain(executor):
    executor._prompt_confirmation.return_value = ConfirmationChoice.NO
    script = "echo one && git status"

    result = asyncio.run(executor.execute_script(script))

    assert result.was_cancelled
    executor._prompt_confirmation.assert_called_once()
    assert executor._prompt_confirmation.call_args.args[0] == script
    executor._run_subprocess.assert_not_awaited()


def test_chain_stops_on_failure(tmp_path):
    executor = SafeExecutor(CommandValidator(), Config(), history=Mock())

    result = asyncio.run(executor.execute_script(
        "pwd && false && echo unreachable", working_dir=str(tmp_path),
    ))

    assert not result.success
    assert result.exit_code == 1
    assert result.stdout.strip() == str(tmp_path.resolve())
    assert "unreachable" not in result.stdout
    assert result.script_path == ""
