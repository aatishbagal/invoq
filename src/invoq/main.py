import asyncio
import shutil
import subprocess
import sys
from typing import Annotated, Optional

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from invoq import __version__
from invoq.config import is_first_run, load_config
from invoq.llm.ollama import OllamaClient
from invoq.llm.ollama_manager import check_ollama_running
from invoq.mcp import server as mcp_server
from invoq.prompts.system_prompts import get_command_generation_prompt

console = Console()
app = typer.Typer(name="invoq", no_args_is_help=True)

# -- subcommand groups --

config_app = typer.Typer(name="config", help="Manage configuration.", no_args_is_help=True)
app.add_typer(config_app)

extensions_app = typer.Typer(name="extensions", help="Manage extensions.", no_args_is_help=True)
app.add_typer(extensions_app)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"invoq {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-V", callback=version_callback, is_eager=True, help="Show version and exit."),
    ] = None,
) -> None:
    """invoq - A CLI tool for invoking tasks."""
    invoked = ctx.invoked_subcommand
    if is_first_run() and invoked not in ("setup", "config"):
        console.print("[yellow]First time? Run 'invoq setup' to get started.[/yellow]")
        console.print()


async def run_ask(prompt: str, execute: bool = False) -> None:
    """Run the ask command with LLM integration."""
    config = load_config()

    if not config.llm.model or config.llm.model == "auto":
        console.print("[yellow]No model configured. Run 'invoq setup' first.[/yellow]")
        return

    if not await check_ollama_running(config.llm.api_url):
        console.print("[red]Cannot connect to Ollama.[/red]")
        console.print("")
        console.print("Make sure Ollama is running:")
        console.print("  ollama serve")
        console.print("")
        console.print("Or check if the API URL is correct:")
        console.print(f"  Current: {config.llm.api_url}")
        return

    try:
        client = OllamaClient(model=config.llm.model, api_url=config.llm.api_url)
    except Exception as e:
        console.print(f"[red]Failed to initialize LLM client: {e}[/red]")
        return

    tools = mcp_server.get_tools_for_ollama()
    system_prompt = get_command_generation_prompt()

    with console.status("[bold blue]Thinking...", spinner="dots"):
        try:
            response = await client.generate_with_tools(
                prompt=prompt,
                system_prompt=system_prompt,
                tools=tools,
            )
        except httpx.ConnectError:
            console.print("[red]Connection to Ollama lost.[/red]")
            return
        except httpx.TimeoutException:
            console.print("[red]Request timed out. The model may be loading.[/red]")
            console.print("Try again in a few seconds.")
            return
        except httpx.HTTPStatusError as e:
            body = ""
            try:
                body = e.response.json().get("error", "")
            except Exception:
                body = e.response.text
            if "not found" in body.lower():
                console.print(f"[red]Model '{config.llm.model}' not found.[/red]")
                console.print("")
                console.print("Download it with:")
                console.print(f"  ollama pull {config.llm.model}")
                console.print("")
                console.print("Or run setup again:")
                console.print("  invoq setup")
            else:
                console.print(f"[red]Ollama error: {body or e}[/red]")
            return
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return

    if not response:
        console.print("[yellow]Empty response from model.[/yellow]")
        return

    if "error" in response:
        error_msg = response["error"]
        if "not found" in error_msg.lower():
            console.print(f"[red]Model '{config.llm.model}' not found.[/red]")
            console.print("")
            console.print("Download it with:")
            console.print(f"  ollama pull {config.llm.model}")
            console.print("")
            console.print("Or run setup again:")
            console.print("  invoq setup")
        else:
            console.print(f"[red]Ollama error: {error_msg}[/red]")
        return

    message = response.get("message", {})
    if message.get("tool_calls"):
        tool_calls = mcp_server.parse_ollama_tool_calls(response)

        for call in tool_calls:
            console.print(f"\n[dim]Calling tool: {call.name}[/dim]")
            result = await mcp_server.handle_tool_call(call)

            if result.success:
                if result.output:
                    console.print(
                        Panel(
                            result.output,
                            title=f"{call.name} output",
                            border_style="green",
                        )
                    )
            else:
                console.print(f"[red]Tool error: {result.error}[/red]")
        return

    content = message.get("content", "")
    if content:
        console.print(f"\n{content}")
    else:
        console.print("[yellow]No response from model[/yellow]")


@app.command()
def ask(
    prompt: Annotated[str, typer.Argument(help="Natural language prompt.")],
    execute: Annotated[
        bool,
        typer.Option("--execute", "-e", help="Execute commands automatically."),
    ] = False,
) -> None:
    """Generate and execute commands from natural language."""
    asyncio.run(run_ask(prompt, execute))


@app.command()
def debug() -> None:
    """Run diagnostics."""
    console.print("[bold]Debug info[/bold]")
    console.print(f"  version: {__version__}")


@app.command()
def explain(command: Annotated[str, typer.Argument(help="The command to explain.")]) -> None:
    """Explain a command."""
    console.print(f"[bold]Explaining:[/bold] {command}")


# -- config subcommands --

@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    console.print("[bold]Configuration[/bold]")


# -- extensions subcommands --

@extensions_app.command("list")
def extensions_list() -> None:
    """List installed extensions."""
    console.print("[bold]Extensions[/bold]")


@app.command("self-update")
def self_update() -> None:
    """Update invoq to the latest version."""
    console.print("Checking for updates...")

    try:
        if shutil.which("pipx"):
            subprocess.run(["pipx", "upgrade", "invoq"], check=True)
        else:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--user", "--upgrade", "invoq"],
                check=True,
            )
        console.print("[green]Updated to latest version.[/green]")
    except subprocess.CalledProcessError:
        console.print("[red]Update failed. Try running manually:[/red]")
        if shutil.which("pipx"):
            console.print("  pipx upgrade invoq")
        else:
            console.print("  pip install --user --upgrade invoq")
        raise typer.Exit(1)


@app.command("self-uninstall")
def self_uninstall() -> None:
    """Uninstall invoq from your system."""
    console.print("This will remove invoq from your system.")

    if not Confirm.ask("Continue?", default=False):
        console.print("Cancelled.")
        raise typer.Exit(0)

    try:
        if shutil.which("pipx"):
            subprocess.run(["pipx", "uninstall", "invoq"], check=True)
        else:
            subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "invoq", "-y"],
                check=True,
            )
        console.print("[green]invoq has been removed.[/green]")
        console.print()
        console.print("To also remove config and data:")
        console.print("  rm -rf ~/.config/invoq ~/.local/share/invoq")
    except subprocess.CalledProcessError:
        console.print("[red]Uninstall failed. Try running manually:[/red]")
        if shutil.which("pipx"):
            console.print("  pipx uninstall invoq")
        else:
            console.print("  pip uninstall invoq")
        raise typer.Exit(1)


@app.command()
def setup(
    skip_checks: Annotated[
        bool, typer.Option("--skip-checks", "-s", help="Skip system requirement checks.")
    ] = False,
    model: Annotated[
        Optional[str], typer.Option("--model", "-m", help="Specify model directly, skip selection.")
    ] = None,
) -> None:
    """Interactive setup wizard for first-time configuration."""
    from invoq.cli.setup_command import run_setup

    success = asyncio.run(run_setup(skip_system_check=skip_checks, model=model))
    if not success:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
