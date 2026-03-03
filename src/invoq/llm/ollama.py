from __future__ import annotations

from typing import AsyncIterator

import ollama

from invoq.llm import LLMClient

_CONNECTION_ERROR_MSG = (
    "Could not connect to Ollama at {url}. "
    "Make sure Ollama is installed and running: https://ollama.com"
)


class OllamaClient(LLMClient):
    def __init__(self, model: str, api_url: str) -> None:
        self._model = model
        self._api_url = api_url
        self._client = ollama.AsyncClient(host=api_url)

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        kwargs: dict = {"model": self._model, "prompt": prompt, "stream": False}
        if system_prompt:
            kwargs["system"] = system_prompt
        try:
            response = await self._client.generate(**kwargs)
            return response.response
        except ollama.ResponseError as exc:
            raise ValueError(f"Ollama model error: {exc}") from exc
        except Exception as exc:
            raise ConnectionError(_CONNECTION_ERROR_MSG.format(url=self._api_url)) from exc

    async def generate_stream(self, prompt: str, system_prompt: str | None = None) -> AsyncIterator[str]:
        kwargs: dict = {"model": self._model, "prompt": prompt, "stream": True}
        if system_prompt:
            kwargs["system"] = system_prompt
        try:
            stream = await self._client.generate(**kwargs)
            async for chunk in stream:
                yield chunk.response
        except ollama.ResponseError as exc:
            raise ValueError(f"Ollama model error: {exc}") from exc
        except Exception as exc:
            raise ConnectionError(_CONNECTION_ERROR_MSG.format(url=self._api_url)) from exc

    async def check_connection(self) -> bool:
        try:
            await self._client.list()
            return True
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            response = await self._client.list()
            return [m.model for m in response.models]
        except Exception as exc:
            raise ConnectionError(_CONNECTION_ERROR_MSG.format(url=self._api_url)) from exc

    async def get_model_info(self, model: str) -> dict:
        try:
            response = await self._client.show(model)
            return response.model_dump()
        except ollama.ResponseError as exc:
            raise ValueError(f"Model {model!r} not found or unavailable: {exc}") from exc
        except Exception as exc:
            raise ConnectionError(_CONNECTION_ERROR_MSG.format(url=self._api_url)) from exc
