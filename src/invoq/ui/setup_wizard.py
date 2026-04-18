from __future__ import annotations

import asyncio
from typing import AsyncIterator, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TransferSpeedColumn,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from invoq.system.detector import GPUType, SystemSpecs
from invoq.llm.model_selector import ModelRecommendation, ModelRecommendations
from invoq.llm.ollama_manager import ModelPullProgress, OllamaInfo, OllamaStatus

console = Console()


def display_header() -> None:
    console.print()
    console.print(Panel(
        Text("invoq Setup", justify="center", style="bold"),
        style="cyan",
    ))
    console.print()


def display_system_specs(specs: SystemSpecs) -> None:
    console.print("[bold][1/4] Checking system requirements...[/bold]")
    console.print()

    total_gb = specs.total_ram_mb / 1024
    ram_style = "green" if total_gb >= 8 else ("yellow" if total_gb >= 4 else "red")

    os_str = specs.os_name
    if specs.os_version != "Unknown":
        os_str += f" {specs.os_version}"
    os_str += f" (Linux {specs.kernel_version})"

    console.print(f"        OS: {os_str}")
    console.print(f"       RAM: [{ram_style}]{total_gb:.1f} GB total[/{ram_style}]")
    console.print(f"       CPU: {specs.cpu_name} ({specs.cpu_cores} cores, {specs.cpu_threads} threads)")

    if specs.primary_gpu:
        gpu = specs.primary_gpu
        gpu_str = gpu.name
        if gpu.vram_mb:
            gpu_str += f" ({gpu.vram_mb / 1024:.0f} GB VRAM)"
        if gpu.is_integrated:
            gpu_str += " (integrated, shared memory)"

        extras = []
        if gpu.cuda_available:
            extras.append("CUDA available")
        if gpu.rocm_available:
            extras.append("ROCm available")
        if extras:
            gpu_str += f" [{', '.join(extras)}]"

        gpu_style = "green" if (gpu.cuda_available or gpu.rocm_available) else "yellow"
        console.print(f"       GPU: [{gpu_style}]{gpu_str}[/{gpu_style}]")
    else:
        console.print("       GPU: [yellow]No dedicated GPU detected[/yellow]")

    disk_gb = specs.ollama_dir_free_mb / 1024
    disk_style = "green" if disk_gb >= 10 else ("yellow" if disk_gb >= 5 else "red")
    console.print(f"      Disk: [{disk_style}]{disk_gb:.0f} GB free in ~/.ollama[/{disk_style}]")
    console.print()


def display_ollama_status(info: OllamaInfo) -> None:
    console.print("[bold][2/4] Checking Ollama installation...[/bold]")
    console.print()

    if info.status == OllamaStatus.NOT_INSTALLED:
        console.print("    Status: [red]Ollama is not installed.[/red]")
        console.print()
        console.print("    To install, run:")
        console.print("    curl -fsSL https://ollama.com/install.sh | sh")
    elif info.status == OllamaStatus.INSTALLED_NOT_RUNNING:
        version_str = f" (v{info.version})" if info.version else ""
        console.print(f"    Status: [yellow]Installed{version_str} but not running[/yellow]")
    elif info.status == OllamaStatus.RUNNING:
        version_str = f" (v{info.version})" if info.version else ""
        console.print(f"    Status: [green]Installed and running{version_str}[/green]")
        if info.installed_models:
            models_str = ", ".join(info.installed_models)
            console.print(f"    Models: {len(info.installed_models)} installed ({models_str})")
        else:
            console.print("    Models: None installed")
    elif info.status == OllamaStatus.ERROR:
        console.print(f"    Status: [red]Error: {info.error_message}[/red]")

    console.print()


def display_model_recommendations(recs: ModelRecommendations) -> str:
    console.print("[bold][3/4] Selecting AI model...[/bold]")
    console.print()

    primary = recs.primary_recommendation
    console.print(f"    Based on your system, we recommend: [green]{primary.model_name}[/green]")
    console.print()
    console.print("    Available models:")
    console.print()

    for i, rec in enumerate(recs.recommendations, 1):
        tag = " (recommended)" if rec.is_recommended else ""
        size_str = f"{rec.model_size_mb / 1024:.1f} GB"

        if rec.is_recommended:
            style = "green"
        elif rec.warning:
            style = "yellow"
        else:
            style = ""

        line = f"    [{style}][{i}] {rec.model_name:<28}{tag:<16}{size_str:<10}{rec.description}[/{style}]"
        console.print(line)

    custom_idx = len(recs.recommendations) + 1
    console.print(f"    [{custom_idx}] Enter custom model name")
    console.print()

    choice = prompt_choice(
        "Select",
        [str(i) for i in range(1, custom_idx + 1)],
        default=1,
    )

    if choice == custom_idx:
        return Prompt.ask("    Enter model name")

    return recs.recommendations[choice - 1].model_name


async def display_model_download(
    model: str,
    progress_iterator: AsyncIterator[ModelPullProgress],
) -> bool:
    console.print(f"    Downloading {model}...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(model, total=None)
        success = True

        async for update in progress_iterator:
            if update.status == "error":
                success = False
                break

            if update.total_bytes > 0:
                progress.update(
                    task,
                    total=update.total_bytes,
                    completed=update.completed_bytes,
                    description=f"{model} ({update.status})",
                )
            else:
                progress.update(task, description=f"{model} ({update.status})")

            if update.status == "complete":
                progress.update(task, completed=update.total_bytes)
                break

    console.print()
    return success


def display_verification(success: bool, response_time: float) -> None:
    console.print("[bold][4/4] Verifying setup...[/bold]")
    console.print()

    if success:
        console.print("    Testing model response...")
        style = "green" if response_time < 5 else ("yellow" if response_time < 10 else "red")
        console.print(f"    Model responded in [{style}]{response_time:.1f}s[/{style}]")
        if response_time > 10:
            console.print("    [yellow]Response is slow. Your hardware may struggle with this model.[/yellow]")
    else:
        console.print("    [red]Model test failed. Please check Ollama logs.[/red]")

    console.print()


def display_setup_complete(model: str) -> None:
    content = (
        f"Setup complete!\n"
        f"\n"
        f"Model: {model}\n"
        f"\n"
        f"Try it out:\n"
        f'  invoq ask "list all python files modified today"\n'
        f'  invoq explain "tar -czvf archive.tar.gz folder/"\n'
        f"  invoq debug"
    )
    console.print(Panel(content, style="green"))
    console.print()


def display_ram_warning(total_ram_mb: int) -> None:
    total_gb = total_ram_mb / 1024
    text = (
        f"Your system has {total_gb:.1f} GB total RAM (less than 4 GB recommended).\n"
        "Performance may be limited, but setup can continue."
    )
    console.print(Panel(text, title="Low RAM", style="yellow"))
    console.print()


def display_error(message: str, suggestion: Optional[str] = None) -> None:
    text = message
    if suggestion:
        text += f"\n\n{suggestion}"
    console.print(Panel(text, title="Error", style="red"))
    console.print()


def prompt_confirmation(message: str) -> bool:
    return Confirm.ask(f"    {message}")


def prompt_choice(message: str, choices: List[str], default: int = 1) -> int:
    while True:
        raw = Prompt.ask(f"    {message} [1-{len(choices)}]", default=str(default))
        try:
            value = int(raw)
            if 1 <= value <= len(choices):
                return value
        except ValueError:
            pass
        console.print(f"    Please enter a number between 1 and {len(choices)}")
