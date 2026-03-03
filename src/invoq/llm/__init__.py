from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from invoq.config import Config


class LLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str | None = None) -> str: ...

    @abstractmethod
    async def generate_stream(self, prompt: str, system_prompt: str | None = None) -> AsyncIterator[str]: ...

    @abstractmethod
    async def check_connection(self) -> bool: ...

    @abstractmethod
    async def list_models(self) -> list[str]: ...

    @abstractmethod
    async def get_model_info(self, model: str) -> dict: ...


def get_llm_client(config: Config) -> LLMClient:
    backend = config.llm.backend
    if backend == "ollama":
        from invoq.llm.ollama import OllamaClient
        model = config.llm.model
        if model == "auto":
            from invoq.llm.model_selector import get_recommended_model
            model = get_recommended_model()
        return OllamaClient(model=model, api_url=config.llm.api_url)
    raise ValueError(f"Unsupported backend: {backend!r}. Supported backends: ollama")
