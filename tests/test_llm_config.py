import pytest

from invoq.config import Config, LLMConfig, _build_config, load_config, save_config
from invoq.llm import get_llm_client
from invoq.llm.ollama import OllamaClient


@pytest.mark.parametrize("backend,url", [
    ("ollama", "http://localhost:11434"),
    ("lmstudio", "http://localhost:1234/v1"),
])
@pytest.mark.parametrize("source", ["dataclass", "build", "load"])
def test_backend_default_urls(backend, url, source, tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text(f"llm:\n  backend: {backend}\n")
    monkeypatch.setattr("invoq.config.get_config_path", lambda: path)
    if source == "dataclass":
        llm = LLMConfig(backend=backend)
    elif source == "build":
        llm = _build_config({"llm": {"backend": backend}}).llm
    else:
        llm = load_config().llm
    assert llm.api_url == url


@pytest.mark.parametrize("backend", ["ollama", "lmstudio"])
@pytest.mark.parametrize("url", ["http://custom:9999/v1", "http://localhost:11434"])
def test_explicit_url_is_preserved(backend, url, tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text(f"llm:\n  backend: {backend}\n  api_url: {url}\n")
    monkeypatch.setattr("invoq.config.get_config_path", lambda: path)
    config = load_config()
    assert config.llm.api_url == url
    save_config(config)
    assert load_config().llm == config.llm


def test_lmstudio_null_url_and_roundtrip(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("llm:\n  backend: lmstudio\n  model: my-model\n  api_url: null\n")
    monkeypatch.setattr("invoq.config.get_config_path", lambda: path)
    config = load_config()
    assert config.llm.api_url == "http://localhost:1234/v1"
    save_config(config)
    assert load_config() == config


def test_unknown_backend_is_rejected():
    with pytest.raises(ValueError, match="Supported backends: ollama, lmstudio"):
        LLMConfig(backend="unknown")


def test_ollama_factory_still_resolves_auto_model(monkeypatch):
    monkeypatch.setattr("invoq.llm.model_selector.get_recommended_model", lambda: "test-model")
    client = get_llm_client(Config())
    assert isinstance(client, OllamaClient)
    assert client._model == "test-model"
    assert client._api_url == "http://localhost:11434"
