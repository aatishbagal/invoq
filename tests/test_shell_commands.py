from importlib import import_module
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invoq.shell.installation import SOURCE_LINE


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("SHELL", "/bin/bash")
    return tmp_path



@pytest.mark.parametrize("script_exists,sourced", [(False, False), (True, False), (False, True), (True, True)])
def test_status_distinguishes_partial_installations(home, monkeypatch, script_exists, sourced):
    cli = import_module("invoq.main")
    monkeypatch.setattr(cli, "is_first_run", lambda: False)
    script = home / ".config/invoq/shell_hook.sh"
    if script_exists:
        script.parent.mkdir(parents=True)
        script.write_text("# hook\n")
    if sourced:
        (home / ".bashrc").write_text(SOURCE_LINE + "\n")

    result = CliRunner().invoke(cli.app, ["shell", "status"])

    assert result.exit_code == 0
    expected = "installed" if script_exists and sourced else "not installed"
    assert f"Shell hooks: {expected}" in result.output
    assert f"Hook script: {'exists' if script_exists else 'missing'}" in result.output
    assert "not created yet" in result.output



def test_cli_install_denial_writes_nothing(home, monkeypatch):
    cli = import_module("invoq.main")
    monkeypatch.setattr(cli, "is_first_run", lambda: False)
    result = CliRunner().invoke(cli.app, ["shell", "install"], input="n\n", terminal_width=200)
    assert result.exit_code == 0
    assert SOURCE_LINE in result.output
    assert "Cancelled" in result.output
    assert list(home.iterdir()) == []



def test_cli_install_and_uninstall(home, monkeypatch):
    cli = import_module("invoq.main")
    monkeypatch.setattr(cli, "is_first_run", lambda: False)
    runner = CliRunner()
    installed = runner.invoke(cli.app, ["shell", "install"], input="y\n")
    assert installed.exit_code == 0, installed.output
    assert "Restart your shell" in installed.output
    removed = runner.invoke(cli.app, ["shell", "uninstall"])
    assert removed.exit_code == 0, removed.output
    assert "history has been preserved" in removed.output
