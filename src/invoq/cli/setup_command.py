from __future__ import annotations

import asyncio
from typing import Optional

from rich.console import Console

from invoq.system.detector import get_system_specs, SystemSpecs
from invoq.llm.model_selector import get_model_recommendations, AVAILABLE_MODELS
from invoq.llm.ollama_manager import (
    check_ollama_running,
    get_install_instructions,
    get_ollama_info,
    list_installed_models,
    OllamaStatus,
    pull_model,
    start_ollama,
    verify_model,
)
from invoq.ui.setup_wizard import (
    console,
    display_error,
    display_header,
    display_model_download,
    display_model_recommendations,
    display_ollama_status,
    display_ram_warning,
    display_setup_complete,
    display_system_specs,
    display_verification,
    prompt_confirmation,
)
from invoq.config import load_config, save_config

console = Console()


async def run_setup(
    skip_system_check: bool = False,
    model: Optional[str] = None,
) -> bool:
    display_header()

    config = load_config()
    if config.llm.backend == "lmstudio":
        console.print(
            "For LM Studio, start its local server and set llm.model to an explicit "
            "identifier from /v1/models in ~/.config/invoq/config.yaml. "
            "Set setup_completed: true after configuration. "
            "The automatic setup wizard currently supports Ollama only."
        )
        return False

    # 1. System detection
    specs: Optional[SystemSpecs] = None
    if not skip_system_check:
        with console.status("[bold]Detecting system hardware...[/bold]"):
            specs = get_system_specs()

        display_system_specs(specs)

        if specs.total_ram_mb < 4000:
            display_ram_warning(specs.total_ram_mb)
            if not prompt_confirmation("Continue anyway?"):
                return False
    else:
        specs = get_system_specs()

    # 2. Ollama check
    api_url = config.llm.api_url
    info = await get_ollama_info(api_url)
    display_ollama_status(info)

    if info.status == OllamaStatus.NOT_INSTALLED:
        console.print()
        console.print("    Install Ollama yourself; invoq does not install Ollama.")
        console.print(f"    {get_install_instructions()}")
        console.print()
        if not prompt_confirmation("Have you installed Ollama? Continue?"):
            return False
        # Re-check after user says they installed
        info = await get_ollama_info(api_url)
        if info.status == OllamaStatus.NOT_INSTALLED:
            display_error("Ollama is still not installed.", suggestion="Run the install command and try again.")
            return False

    if info.status == OllamaStatus.INSTALLED_NOT_RUNNING:
        if prompt_confirmation("Start Ollama now?"):
            console.print("    Starting Ollama...")
            started = await start_ollama()
            if not started:
                display_error(
                    "Failed to start Ollama.",
                    suggestion="Try running 'ollama serve' manually in another terminal.",
                )
                return False
            console.print("    [green]Ollama started.[/green]")
            console.print()
            info = await get_ollama_info(api_url)
        else:
            display_error("Ollama must be running to continue.")
            return False

    if info.status == OllamaStatus.ERROR:
        display_error(
            f"Ollama error: {info.error_message}",
            suggestion="Check Ollama logs with 'journalctl -u ollama'.",
        )
        return False

    # 3. Model selection
    selected_model: str
    if model:
        selected_model = model
        console.print(f"[bold][3/4] Using specified model:[/bold] {selected_model}")
        console.print()
    else:
        recs = get_model_recommendations(specs)
        selected_model = display_model_recommendations(recs)

    # 4. Model download
    installed_models = await list_installed_models(api_url)
    if selected_model in installed_models:
        console.print(f"    [green]{selected_model} is already installed.[/green]")
        console.print()
    else:
        progress = pull_model(selected_model, api_url)
        success = await display_model_download(selected_model, progress)
        if not success:
            display_error(
                f"Failed to download {selected_model}.",
                suggestion=f"Try running 'ollama pull {selected_model}' manually.",
            )
            return False

    # 5. Verification
    console.print("[bold][4/4] Verifying setup...[/bold]")
    console.print("    Testing model response...")
    success, response_time = await verify_model(selected_model, api_url)
    display_verification(success, response_time)

    if not success:
        display_error(
            "Model verification failed.",
            suggestion="Try running 'ollama run " + selected_model + "' to test manually.",
        )
        return False

    # 6. Save config
    config.llm.model = selected_model
    config.setup_completed = True
    save_config(config)

    # 7. Complete
    display_setup_complete(selected_model)
    return True
