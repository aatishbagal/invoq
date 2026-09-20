import pytest

from invoq.config import Config, load_config, save_config


def test_remediation_enabled_by_default():
    assert Config().security.remediation_mode is True


@pytest.mark.parametrize("contents", ["", "execution:\n  require_confirmation: false\n"])
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
