from __future__ import annotations

from typing import AsyncIterator, Optional

import httpx
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

    async def generate_with_tools(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> dict:
        """Generate a response with tool calling support."""
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._api_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def get_model_info(self, model: str) -> dict:
        try:
            response = await self._client.show(model)
            return response.model_dump()
        except ollama.ResponseError as exc:
            raise ValueError(f"Model {model!r} not found or unavailable: {exc}") from exc
        except Exception as exc:
            raise ConnectionError(_CONNECTION_ERROR_MSG.format(url=self._api_url)) from exc
