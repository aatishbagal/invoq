from dataclasses import asdict
from importlib import import_module
from importlib.resources import files
from pathlib import Path

import pytest
import yaml

from invoq.config import Config, load_config, save_config


pytestmark = pytest.mark.security


def test_remediation_enabled_by_default():
    assert Config().security.remediation_mode is True


@pytest.mark.parametrize("contents", ["", "llm:\n  model: existing-model\n"])
def test_existing_configs_enable_remediation(tmp_path, monkeypatch, contents):
    path = tmp_path / "config.yaml"
    path.write_text(contents)
    monkeypatch.setattr("invoq.config.get_config_path", lambda: path)

    assert load_config().security.remediation_mode is True


@pytest.mark.parametrize("enabled", [True, False])
def test_remediation_config_roundtrip(tmp_path, monkeypatch, enabled):
    monkeypatch.setattr("invoq.config.get_config_path", lambda: tmp_path / "config.yaml")
    config = Config()
    config.security.remediation_mode = enabled

    save_config(config)

    assert load_config().security.remediation_mode is enabled


@pytest.mark.parametrize("value", ['"false"', "null", "0", "[]"])
def test_invalid_remediation_values_fail_closed(tmp_path, monkeypatch, value):
    path = tmp_path / "config.yaml"
    path.write_text(f"security:\n  remediation_mode: {value}\n")
    monkeypatch.setattr("invoq.config.get_config_path", lambda: path)

    with pytest.raises(ValueError, match="security.remediation_mode must be a boolean"):
        load_config()


def test_execution_settings_are_absent_from_config_schema():
    assert not hasattr(import_module("invoq.config"), "ExecutionConfig")
    assert "execution" not in asdict(Config())
    with pytest.raises(TypeError):
        Config(execution={})


@pytest.mark.parametrize("source", ["package", "repository"])
def test_defaults_do_not_advertise_execution_settings(source):
    path = (
        files("invoq").joinpath("default.yaml")
        if source == "package"
        else Path(__file__).resolve().parents[1] / "config" / "default.yaml"
    )
    assert "execution" not in yaml.safe_load(path.read_text(encoding="utf-8"))


def test_saved_config_does_not_restore_execution_settings(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    monkeypatch.setattr("invoq.config.get_config_path", lambda: path)

    config = load_config()
    save_config(config)

    assert "execution" not in yaml.safe_load(path.read_text())
    assert not hasattr(load_config(), "execution")


@pytest.mark.parametrize("setting", [
    "allow_sudo_bypass", "require_confirmation", "show_command_explanation",
])
@pytest.mark.parametrize("value", ["true", "false"])
def test_removed_execution_settings_require_migration(tmp_path, monkeypatch, setting, value):
    path = tmp_path / "config.yaml"
    contents = f"execution:\n  {setting}: {value}\n"
    path.write_text(contents)
    monkeypatch.setattr("invoq.config.get_config_path", lambda: path)

    with pytest.raises(ValueError, match="Remove the unsupported 'execution' section"):
        load_config()

    assert path.read_text() == contents


@pytest.mark.parametrize("value", ["{}", "null", "false", "[]"])
def test_removed_execution_section_is_rejected_regardless_of_value(tmp_path, monkeypatch, value):
    path = tmp_path / "config.yaml"
    path.write_text(f"execution: {value}\n")
    monkeypatch.setattr("invoq.config.get_config_path", lambda: path)

    with pytest.raises(ValueError, match="Remove the unsupported 'execution' section"):
        load_config()
