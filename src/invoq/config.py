from __future__ import annotations

from dataclasses import dataclass, field, asdict
from importlib.resources import files
from pathlib import Path

import yaml

_CONFIG_DIR = "invoq"
_CONFIG_FILE = "config.yaml"


@dataclass
class LLMConfig:
    backend: str = "ollama"
    model: str = "auto"
    api_url: str = "http://localhost:11434"


@dataclass
class SecurityConfig:
    remediation_mode: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.remediation_mode, bool):
            raise ValueError("security.remediation_mode must be a boolean")


@dataclass
class ExtensionsConfig:
    enabled: list[str] = field(default_factory=lambda: ["git"])


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    extensions: ExtensionsConfig = field(default_factory=ExtensionsConfig)
    setup_completed: bool = False
    security: SecurityConfig = field(default_factory=SecurityConfig)


def get_config_path() -> Path:
    return Path.home() / ".config" / _CONFIG_DIR / _CONFIG_FILE


def ensure_config_dir() -> Path:
    config_dir = get_config_path().parent
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_default_data() -> dict:
    raw = files("invoq").joinpath("default.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(raw) or {}


def _build_config(data: dict) -> Config:
    if "execution" in data:
        raise ValueError(
            "Remove the unsupported 'execution' section from config.yaml; "
            "its settings were never enforced. See docs/configuration.md for migration."
        )
    llm = data.get("llm", {})
    security = data.get("security", {})
    extensions = data.get("extensions", {})
    return Config(
        llm=LLMConfig(
            backend=llm.get("backend", "ollama"),
            model=llm.get("model", "auto"),
            api_url=llm.get("api_url", "http://localhost:11434"),
        ),
        security=SecurityConfig(
            remediation_mode=security.get("remediation_mode", True),
        ),
        extensions=ExtensionsConfig(
            enabled=extensions.get("enabled", ["git"]),
        ),
        setup_completed=data.get("setup_completed", False),
    )


def load_config() -> Config:
    merged = _load_default_data()

    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                user_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Malformed config at {config_path}: {exc}") from exc
        merged = _deep_merge(merged, user_data)

    return _build_config(merged)


def save_config(config: Config) -> None:
    ensure_config_dir()
    with open(get_config_path(), "w", encoding="utf-8") as f:
        yaml.dump(asdict(config), f, default_flow_style=False, sort_keys=False)


def is_first_run() -> bool:
    """Check if setup has been completed."""
    config_path = get_config_path()
    if not config_path.exists():
        return True

    try:
        config = load_config()
        return not getattr(config, "setup_completed", False)
    except Exception:
        return True
