from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "default.yaml"


def load_config(path: Path | None = None) -> dict:
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f) or {}
