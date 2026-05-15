from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from invoq.config import Config
from invoq.core.executor import (
    ConfirmationChoice,
    ExecutionResult,
    SafeExecutor,
    ScriptExecutionResult,
)
from invoq.core.history import CommandHistory
from invoq.core.validator import CommandValidator


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture
def validator() -> CommandValidator:
    # Allow sleep as an extension command so timeout tests can run
    return CommandValidator(extension_commands={"sleep"})


@pytest.fixture
def history(tmp_path, monkeypatch) -> CommandHistory:
    monkeypatch.setattr(
        "invoq.core.history.get_history_path",
        lambda: tmp_path / "history.json",
    )
    return CommandHistory()


@pytest.fixture
def executor(
    validator: CommandValidator, config: Config, history: CommandHistory
) -> SafeExecutor:
    return SafeExecutor(validator, config, timeout_seconds=5, history=history)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


class TestExecute:
    def test_execute_safe_command(self, executor: SafeExecutor) -> None:
        with patch.object(executor, "_prompt_confirmation") as mock_prompt:
            result = _run(executor.execute("ls -la"))
            mock_prompt.assert_not_called()
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.exit_code == 0

    def test_execute_blocked_command(self, executor: SafeExecutor) -> None:
        result = _run(executor.execute("rm -rf /"))
        assert result.was_blocked is True
        assert result.block_reason is not None
        assert result.success is False

    def test_execute_confirm_approved(self, executor: SafeExecutor) -> None:
        with patch.object(
            executor, "_prompt_confirmation", return_value=ConfirmationChoice.YES
        ):
            result = _run(executor.execute("git --version"))
        assert result.success is True
        assert result.was_cancelled is False

    def test_execute_confirm_denied(self, executor: SafeExecutor) -> None:
        with patch.object(
            executor, "_prompt_confirmation", return_value=ConfirmationChoice.NO
        ):
            result = _run(executor.execute("git status"))
        assert result.was_cancelled is True
        assert result.success is False

    def test_execute_with_timeout(
        self,
        validator: CommandValidator,
        config: Config,
        history: CommandHistory,
    ) -> None:
        ex = SafeExecutor(validator, config, timeout_seconds=1, history=history)
        result = _run(ex.execute("sleep 10", skip_confirmation=True))
        assert result.was_timeout is True
        assert result.success is False

    def test_execute_captures_stdout(self, executor: SafeExecutor) -> None:
        result = _run(executor.execute("echo hello"))
        assert "hello" in result.stdout

    def test_execute_captures_stderr(self, executor: SafeExecutor) -> None:
        result = _run(executor.execute("ls /nonexistent_path_xyz_123"))
        assert result.stderr != ""
        assert result.failed is True


class TestExecuteScript:
    def test_script_validates_all_commands(self, executor: SafeExecutor) -> None:
        script = "echo safe\nrm -rf /tmp/anything"
        result = _run(executor.execute_script(script, skip_confirmation=True))
        assert isinstance(result, ScriptExecutionResult)
        assert len(result.commands_blocked) > 0
        assert result.success is False

    def test_script_runs_safe_commands(self, executor: SafeExecutor) -> None:
        script = "echo one\necho two\necho three"
        result = _run(executor.execute_script(script, skip_confirmation=True))
        assert result.success is True
        assert "one" in result.stdout
        assert "two" in result.stdout
        assert "three" in result.stdout
