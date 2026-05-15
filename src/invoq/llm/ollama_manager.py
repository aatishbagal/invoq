from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, List, Optional

import httpx


class OllamaStatus(Enum):
    NOT_INSTALLED = "not_installed"
    INSTALLED_NOT_RUNNING = "installed_not_running"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class OllamaInfo:
    status: OllamaStatus
    version: Optional[str]
    api_url: str
    models_dir: str
    installed_models: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class ModelPullProgress:
    model: str
    status: str  # 'downloading', 'verifying', 'complete', 'error'
    completed_bytes: int
    total_bytes: int
    percent: float
    error_message: Optional[str] = None


def check_ollama_installed() -> bool:
    return shutil.which("ollama") is not None


def get_ollama_version() -> Optional[str]:
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            # Format: "ollama version 0.x.y" or just "0.x.y"
            parts = output.split()
            return parts[-1] if parts else output
        return None
    except (subprocess.TimeoutExpired, OSError):
        return None


async def check_ollama_running(api_url: str = "http://localhost:11434") -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{api_url}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


async def start_ollama() -> bool:
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return False

    # Wait up to 10 seconds for API
    for _ in range(20):
        await asyncio.sleep(0.5)
        if await check_ollama_running():
            return True

    return False


async def list_installed_models(api_url: str = "http://localhost:11434") -> List[str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{api_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []


async def get_ollama_info(api_url: str = "http://localhost:11434") -> OllamaInfo:
    models_dir = os.environ.get("OLLAMA_MODELS", str(os.path.expanduser("~/.ollama")))

    if not check_ollama_installed():
        return OllamaInfo(
            status=OllamaStatus.NOT_INSTALLED,
            version=None,
            api_url=api_url,
            models_dir=models_dir,
        )

    version = get_ollama_version()

    running = await check_ollama_running(api_url)
    if not running:
        return OllamaInfo(
            status=OllamaStatus.INSTALLED_NOT_RUNNING,
            version=version,
            api_url=api_url,
            models_dir=models_dir,
        )

    try:
        models = await list_installed_models(api_url)
        return OllamaInfo(
            status=OllamaStatus.RUNNING,
            version=version,
            api_url=api_url,
            models_dir=models_dir,
            installed_models=models,
        )
    except Exception as exc:
        return OllamaInfo(
            status=OllamaStatus.ERROR,
            version=version,
            api_url=api_url,
            models_dir=models_dir,
            error_message=str(exc),
        )


def get_install_instructions() -> str:
    return (
        "To install Ollama, run:\n"
        "\n"
        "  curl -fsSL https://ollama.com/install.sh | sh\n"
        "\n"
        "You may need to use sudo if prompted."
    )


async def pull_model(
    model: str,
    api_url: str = "http://localhost:11434",
) -> AsyncIterator[ModelPullProgress]:
    url = f"{api_url}/api/pull"

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                url,
                json={"name": model, "stream": True},
                timeout=None,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    yield ModelPullProgress(
                        model=model,
                        status="error",
                        completed_bytes=0,
                        total_bytes=0,
                        percent=0.0,
                        error_message=f"HTTP {response.status_code}: {body.decode(errors='replace')}",
                    )
                    return

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue

                    if "error" in data:
                        yield ModelPullProgress(
                            model=model,
                            status="error",
                            completed_bytes=0,
                            total_bytes=0,
                            percent=0.0,
                            error_message=str(data["error"]),
                        )
                        return

                    status_text = data.get("status", "")
                    total = data.get("total", 0)
                    completed = data.get("completed", 0)
                    percent = (completed / total * 100.0) if total > 0 else 0.0

                    if "pulling" in status_text or "downloading" in status_text:
                        pull_status = "downloading"
                    elif "verifying" in status_text:
                        pull_status = "verifying"
                    elif "success" in status_text:
                        pull_status = "complete"
                    else:
                        pull_status = status_text or "downloading"

                    yield ModelPullProgress(
                        model=model,
                        status=pull_status,
                        completed_bytes=completed,
                        total_bytes=total,
                        percent=percent,
                    )

                    if pull_status == "complete":
                        return

    except httpx.ConnectError:
        yield ModelPullProgress(
            model=model,
            status="error",
            completed_bytes=0,
            total_bytes=0,
            percent=0.0,
            error_message="Cannot connect to Ollama. Is it running? Try 'ollama serve'",
        )
    except Exception as exc:
        yield ModelPullProgress(
            model=model,
            status="error",
            completed_bytes=0,
            total_bytes=0,
            percent=0.0,
            error_message=str(exc),
        )


async def delete_model(model: str, api_url: str = "http://localhost:11434") -> bool:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(
                "DELETE", f"{api_url}/api/delete", json={"name": model},
            )
            return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException, OSError):
        return False


async def verify_model(
    model: str,
    api_url: str = "http://localhost:11434",
) -> tuple[bool, float]:
    try:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{api_url}/api/generate",
                json={
                    "model": model,
                    "prompt": "Reply with just the word: hello",
                    "stream": False,
                },
            )
            elapsed = time.monotonic() - start
            return response.status_code == 200, elapsed
    except (httpx.ConnectError, httpx.TimeoutException, OSError):
        return False, 0.0
