from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from invoq.llm import LLMClient


class LMStudioClient(LLMClient):
    def __init__(self, model: str, api_url: str) -> None:
        self._model = model
        self._api_url = api_url.rstrip("/")

    def _payload(self, prompt: str, system_prompt: str | None, stream: bool) -> dict:
        if not self._model or self._model == "auto":
            raise ValueError(
                "LM Studio requires an explicit llm.model identifier from /v1/models; "
                "automatic model selection is only supported for Ollama."
            )
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return {"model": self._model, "messages": messages, "stream": stream}

    def _connection_error(self) -> ConnectionError:
        return ConnectionError(
            f"LM Studio not reachable at {self._api_url} - "
            "is the LM Studio server running with a model loaded?"
        )

    def _api_error(self, error: object) -> ValueError:
        detail = str(error)
        if "tool" in detail.lower() or "function calling" in detail.lower():
            return ValueError(
                f"LM Studio tool-calling error for model {self._model!r}: {detail}. "
                "Load a model with tool-calling support in LM Studio and set llm.model "
                "to its identifier."
            )
        return ValueError(f"LM Studio API error: {detail}")

    def _decode(self, text: str) -> dict:
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise ValueError("LM Studio returned invalid JSON.") from exc
        if not isinstance(data, dict):
            raise ValueError("LM Studio returned an invalid response object.")
        if "error" in data:
            raise self._api_error(data["error"])
        return data

    def _check_status(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise self._api_error(
                f"HTTP {response.status_code}: {response.text}"
            ) from exc

    async def _request(
        self, method: str, endpoint: str, payload: dict | None = None, timeout: float = 120.0,
    ) -> dict:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method, f"{self._api_url}/{endpoint}", json=payload,
                )
                self._check_status(response)
                return self._decode(response.text)
        except httpx.RequestError as exc:
            raise self._connection_error() from exc

    @staticmethod
    def _message(data: dict) -> dict:
        try:
            message = data["choices"][0]["message"]
            if not isinstance(message, dict):
                raise TypeError
            content = message.get("content")
            if content is not None and not isinstance(content, str):
                raise TypeError
            return {**message, "content": content or ""}
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("LM Studio returned an invalid chat completion.") from exc

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        data = await self._request(
            "POST", "chat/completions", self._payload(prompt, system_prompt, False),
        )
        message = self._message(data)
        if message.get("tool_calls"):
            raise ValueError(
                "LM Studio returned unexpected tool calls for a text request; "
                "use generate_with_tools() for tool calling."
            )
        return message["content"]

    async def generate_stream(
        self, prompt: str, system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        payload = self._payload(prompt, system_prompt, True)
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", f"{self._api_url}/chat/completions", json=payload,
                ) as response:
                    if not response.is_success:
                        await response.aread()
                        self._check_status(response)
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        event = line[5:].strip()
                        if event == "[DONE]":
                            return
                        if not event:
                            continue
                        data = self._decode(event)
                        try:
                            choices = data["choices"]
                            if choices == []:
                                continue
                            delta = choices[0]["delta"]
                            if not isinstance(delta, dict):
                                raise TypeError
                            content = delta.get("content")
                            if content is not None and not isinstance(content, str):
                                raise TypeError
                        except (KeyError, IndexError, TypeError) as exc:
                            raise ValueError("LM Studio returned an invalid stream chunk.") from exc
                        if delta.get("tool_calls"):
                            raise ValueError(
                                "LM Studio returned unexpected streaming tool calls; "
                                "use generate_with_tools() for tool calling."
                            )
                        if content:
                            yield content
                    raise ValueError("LM Studio stream ended before the [DONE] event.")
        except httpx.RequestError as exc:
            raise self._connection_error() from exc

    async def check_connection(self) -> bool:
        try:
            data = await self._request("GET", "models", timeout=5.0)
            self._models(data)
            return True
        except (ConnectionError, ValueError):
            return False

    @staticmethod
    def _models(data: dict) -> list[dict]:
        models = data.get("data")
        if not isinstance(models, list) or any(
            not isinstance(model, dict) or not isinstance(model.get("id"), str)
            for model in models
        ):
            raise ValueError("LM Studio returned an invalid model list.")
        return models

    async def list_models(self) -> list[str]:
        data = await self._request("GET", "models")
        return [model["id"] for model in self._models(data)]

    async def get_model_info(self, model: str) -> dict:
        data = await self._request("GET", "models")
        for info in self._models(data):
            if info["id"] == model:
                return info
        raise ValueError(
            f"LM Studio model {model!r} not found or unavailable. "
            "Load it in LM Studio and check its identifier in /v1/models."
        )

    async def generate_with_tools(
        self, prompt: str, system_prompt: str | None = None, tools: list | None = None,
    ) -> dict:
        payload = self._payload(prompt, system_prompt, False)
        if tools:
            payload["tools"] = tools
        data = await self._request("POST", "chat/completions", payload)
        message = self._message(data)
        calls = message.get("tool_calls")
        if calls is None:
            calls = []
        if not isinstance(calls, list):
            raise ValueError("LM Studio returned an invalid tool call list.")
        if data["choices"][0].get("finish_reason") == "tool_calls" and not calls:
            raise ValueError("LM Studio reported tool calls but returned none.")
        if calls and not tools:
            raise ValueError("LM Studio returned tool calls when no tools were requested.")
        normalized = []
        for call in calls:
            try:
                function = call["function"]
                name = function["name"]
                arguments = function["arguments"]
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                if not isinstance(name, str) or not name or not isinstance(arguments, dict):
                    raise ValueError
                normalized.append({**call, "function": {**function, "arguments": arguments}})
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    "LM Studio returned a malformed tool call. "
                    "Use a model with tool-calling support; arguments must be a JSON object."
                ) from exc
        message["tool_calls"] = normalized
        return {**data, "message": message}
