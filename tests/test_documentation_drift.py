import asyncio
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from typer.testing import CliRunner
import yaml

from invoq.config import Config, _build_config, load_config, save_config


pytestmark = pytest.mark.security
ROOT = Path(__file__).resolve().parents[1]
cli = import_module("invoq.main")
runner = CliRunner()


@pytest.fixture(autouse=True)
def configured_cli(monkeypatch):
    monkeypatch.setattr(cli, "is_first_run", lambda: False)


@pytest.mark.parametrize("command", [["debug"], ["extensions", "list"]])
def test_unimplemented_commands_report_failure(command):
    result = runner.invoke(cli.app, command)

    assert result.exit_code == 1
    assert "not yet implemented" in result.output.lower()
    assert "version:" not in result.output


@pytest.mark.parametrize("command", [[], ["debug"], ["extensions"], ["extensions", "list"]])
def test_help_labels_unimplemented_commands(command):
    result = runner.invoke(cli.app, [*command, "--help"], terminal_width=120)

    assert result.exit_code == 0
    assert "not yet implemented" in result.output.lower()
    assert "Manage extensions" not in result.output
    assert "Run diagnostics" not in result.output


@pytest.mark.parametrize("flag", ["--execute", "-e"])
def test_ask_rejects_removed_execution_flag(monkeypatch, flag):
    run = AsyncMock()
    monkeypatch.setattr(cli, "run_ask", run)

    result = runner.invoke(cli.app, ["ask", "hello", flag])

    assert result.exit_code == 2
    run.assert_not_awaited()


def test_ask_help_describes_policy_gate():
    result = runner.invoke(cli.app, ["ask", "--help"], terminal_width=120)

    assert result.exit_code == 0
    assert "--execute" not in result.output
    assert "policy" in result.output.lower()
    assert "confirmation" in result.output.lower()


def test_ask_passes_only_prompt(monkeypatch):
    run = AsyncMock()
    monkeypatch.setattr(cli, "run_ask", run)

    result = runner.invoke(cli.app, ["ask", "list files"])

    assert result.exit_code == 0
    run.assert_awaited_once_with("list files")


def test_ask_tool_calls_still_use_mcp_gate(monkeypatch):
    config = Config()
    config.llm.model = "test-model"
    client = SimpleNamespace(generate_with_tools=AsyncMock(return_value={
        "message": {"tool_calls": [{"function": {
            "name": "execute_command", "arguments": {"command": "echo hello"},
        }}]},
    }))
    gate = AsyncMock(return_value=SimpleNamespace(success=False, error="BLOCKED: test"))
    monkeypatch.setattr(cli, "load_config", lambda: config)
    monkeypatch.setattr(cli, "check_ollama_running", AsyncMock(return_value=True))
    monkeypatch.setattr(cli, "OllamaClient", Mock(return_value=client))
    monkeypatch.setattr(type(cli.mcp_server), "handle_tool_call", gate)

    result = runner.invoke(cli.app, ["ask", "say hello"])

    assert result.exit_code == 0
    gate.assert_awaited_once()
    assert gate.call_args.args[0].name == "execute_command"
    assert "Blocked" in result.output


@pytest.mark.parametrize("source", ["dataclass", "fallback", "package", "repository", "saved"])
def test_extensions_are_disabled_by_default(tmp_path, monkeypatch, source):
    path = tmp_path / "config.yaml"
    monkeypatch.setattr("invoq.config.get_config_path", lambda: path)
    if source == "dataclass":
        config = Config()
    elif source == "fallback":
        config = _build_config({})
    elif source == "repository":
        config = _build_config(yaml.safe_load((ROOT / "config/default.yaml").read_text()))
    else:
        config = load_config()
        if source == "saved":
            save_config(config)
            config = load_config()

    assert config.extensions.enabled == []






def test_readme_describes_current_cli_contract():
    text = " ".join((ROOT / "README.md").read_text().split())

    assert "Debug last failed command" not in text
    assert "debug` is not yet implemented" in text
    assert "Extensions are not yet implemented" in text
    assert "`--execute`" in text and "removed" in text


def test_configuration_docs_do_not_enable_git():
    text = (ROOT / "docs/configuration.md").read_text()
    defaults = yaml.safe_load(text.split("```yaml\n", 1)[1].split("```", 1)[0])

    assert defaults["extensions"]["enabled"] == []
    assert "not yet implemented" in text
