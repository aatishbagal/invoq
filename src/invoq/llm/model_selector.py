from __future__ import annotations

import psutil
import ollama


# RAM thresholds in GB
_MIN_RAM_GB = 4.0
_MID_LOW_RAM_GB = 6.0
_MID_HIGH_RAM_GB = 8.0

# Model tiers
_MODEL_SMALL = "qwen2.5-coder:1.5b"
_MODEL_MEDIUM = "qwen2.5-coder:7b-q4_0"
_MODEL_FULL = "qwen2.5-coder:7b"


def get_available_ram_gb() -> float:
    return psutil.virtual_memory().available / (1024**3)


def get_recommended_model() -> str:
    ram_gb = get_available_ram_gb()
    if ram_gb < _MIN_RAM_GB:
        raise RuntimeError(
            f"Insufficient RAM: {ram_gb:.1f}GB available, minimum {_MIN_RAM_GB:.0f}GB required"
        )
    if ram_gb < _MID_LOW_RAM_GB:
        return _MODEL_SMALL
    if ram_gb < _MID_HIGH_RAM_GB:
        return _MODEL_MEDIUM
    return _MODEL_FULL


def check_model_available(model: str) -> bool:
    try:
        client = ollama.Client()
        response = client.list()
        available = [m.model for m in response.models]
        return model in available
    except Exception:
        return False


def suggest_model_download() -> str:
    model = get_recommended_model()
    return f"ollama pull {model}"
