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
from rich.syntax import Syntax

from invoq import __version__
from invoq.config import is_first_run, load_config
from invoq.llm import get_llm_client
from invoq.mcp import server as mcp_server
from invoq.mcp.types import ToolCall
from invoq.prompts.system_prompts import build_ask_prompt

console = Console()
_HELP_OPTIONS = {"help_option_names": ["-h", "--h", "--help"]}
app = typer.Typer(name="invoq", no_args_is_help=True, context_settings=_HELP_OPTIONS)

# -- subcommand groups --

config_app = typer.Typer(
    name="config",
    help="Manage configuration.",
    no_args_is_help=True,
    context_settings=_HELP_OPTIONS,
)
app.add_typer(config_app)

extensions_app = typer.Typer(
    name="extensions",
    help="Extensions are not yet implemented.",
    no_args_is_help=True,
    context_settings=_HELP_OPTIONS,
)
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
        typer.Option(
            "--version",
            "-V",
            "-v",
            "--v",
            "--V",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
) -> None:
    """invoq - A CLI tool for invoking tasks."""
    invoked = ctx.invoked_subcommand
    if is_first_run() and invoked not in ("setup", "config"):
        console.print("[yellow]First time? Run 'invoq setup' to get started.[/yellow]")
        console.print()


async def run_ask(prompt: str) -> None:
    """Run the ask command with LLM integration."""
    config = load_config()

    if not config.llm.model or config.llm.model == "auto":
        if config.llm.backend == "lmstudio":
            console.print("Set llm.model to an explicit LM Studio model identifier from /v1/models.")
        else:
            console.print("[yellow]No model configured. Run 'invoq setup' first.[/yellow]")
        return

    try:
        client = get_llm_client(config)
    except Exception as e:
        console.print(f"[red]Failed to initialize LLM client: {e}[/red]")
        return

    if not await client.check_connection():
        if config.llm.backend == "lmstudio":
            console.print("LM Studio not reachable - is the LM Studio server running with a model loaded?")
        else:
            console.print("[red]Cannot connect to Ollama.[/red] Start it with: ollama serve")
        console.print(f"Check the API URL: {config.llm.api_url}")
        return

    tools = mcp_server.get_tools_for_ollama()
    system_prompt = build_ask_prompt()

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

    tool_calls = mcp_server.parse_ollama_tool_calls(response)
    message = response.get("message", {})
    content = message.get("content", "")

    if tool_calls:
        for call in tool_calls:
            await execute_tool_call(call)
    elif content:
        console.print(f"\n{content}")
    else:
        console.print("[yellow]No response from model.[/yellow]")


async def execute_tool_call(call: ToolCall) -> None:
    """Execute a single tool call with appropriate UI."""
    tool_name = call.name
    args = call.arguments

    if tool_name == "execute_command":
        command = args.get("command", "")
        console.print("\n[dim]Running command:[/dim]")
        console.print(Panel(Syntax(command, "bash", theme="monokai"), border_style="blue"))
    elif tool_name == "execute_script":
        script = args.get("script", "")
        console.print("\n[dim]Running script:[/dim]")
        console.print(Panel(Syntax(script, "bash", theme="monokai"), border_style="blue"))
    elif tool_name == "read_file":
        path = args.get("path", "")
        console.print(f"\n[dim]Reading file: {path}[/dim]")
    elif tool_name == "list_directory":
        path = args.get("path", ".")
        console.print(f"\n[dim]Listing directory: {path}[/dim]")
    elif tool_name == "get_system_info":
        console.print("\n[dim]Getting system info...[/dim]")
    else:
        console.print(f"\n[dim]Calling {tool_name}...[/dim]")

    result = await mcp_server.handle_tool_call(call)

    if result.success:
        if result.output:
            console.print(
                Panel(result.output, title="[green]Result[/green]", border_style="green")
            )
        else:
            console.print("[green]Done (no output)[/green]")
    else:
        error = result.error or "Unknown error"
        if error.startswith("BLOCKED:"):
            reason = error[len("BLOCKED:"):].strip()
            message = (
                "Destructive or unrecognized commands are disabled for safety.\n"
                f"Reason: {reason}"
            )
            console.print(
                Panel(message, title="[red]Blocked[/red]", border_style="red")
            )
        else:
            console.print(
                Panel(error, title="[red]Error[/red]", border_style="red")
            )


@app.command()
def ask(
    prompt: Annotated[str, typer.Argument(help="Natural language prompt.")],
) -> None:
    """Generate and execute commands through MCP policy and confirmation checks."""
    asyncio.run(run_ask(prompt))


@app.command()
def debug() -> None:
    """Debugging failed commands is not yet implemented."""
    console.print("[yellow]Debugging failed commands is not yet implemented.[/yellow]")
    raise typer.Exit(1)


async def run_explain(command: str) -> None:
    """Run the explain command end-to-end."""
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.spinner import Spinner

    from invoq.core.executor import SafeExecutor
    from invoq.core.explainer import CommandExplainer
    from invoq.core.history import CommandHistory
    from invoq.core.validator import CommandValidator
    from invoq.mcp.client import MCPClient
    from invoq.mcp.confirmation import ConfirmationHandler
    from invoq.mcp.server import InvoqMCPServer

    config = load_config()

    if not config.llm.model or config.llm.model == "auto":
        if config.llm.backend == "lmstudio":
            console.print("Set llm.model to an explicit LM Studio model identifier from /v1/models.")
        else:
            console.print("[yellow]No model configured. Run 'invoq setup' first.[/yellow]")
        raise typer.Exit(1)

    llm_client = get_llm_client(config)

    if not await llm_client.check_connection():
        if config.llm.backend == "lmstudio":
            console.print("LM Studio not reachable - is the LM Studio server running with a model loaded?")
            console.print(f"Check the API URL: {config.llm.api_url}")
        else:
            console.print("[red]Ollama is not running.[/red] Start it with: [bold]ollama serve[/bold]")
        raise typer.Exit(1)

    validator = CommandValidator()
    executor = SafeExecutor(validator=validator, config=config)
    history = CommandHistory()
    confirmation_handler = ConfirmationHandler(validator=validator)
    mcp_server_instance = InvoqMCPServer(
        validator=validator,
        executor=executor,
        history=history,
        confirmation_handler=confirmation_handler,
    )
    mcp_client = MCPClient(llm_client=llm_client, mcp_server=mcp_server_instance)
    explainer = CommandExplainer(mcp_client=mcp_client, validator=validator)

    console.print(f"\n[dim]Explaining:[/dim] [bold]{command}[/bold]\n")

    with Live(Spinner("dots", text="Thinking..."), refresh_per_second=10, transient=True):
        result = await explainer.explain(command)

    if not result.success:
        console.print(f"[red]Error:[/red] {result.error}")
        raise typer.Exit(1)

    for warning in result.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")

    tier_color = {"safe": "green", "confirm": "yellow", "blocked": "red"}.get(
        result.tier, "white"
    )
    console.print(f"[{tier_color}]Tier: {result.tier.upper()}[/{tier_color}]\n")

    console.print(
        Panel(
            Markdown(result.raw_explanation),
            title=f"[bold]{command}[/bold]",
            border_style="blue",
        )
    )


@app.command()
def explain(command: Annotated[str, typer.Argument(help="The command to explain.")]) -> None:
    """Explain what a shell command does."""
    asyncio.run(run_explain(command))


# -- config subcommands --

@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    console.print("[bold]Configuration[/bold]")


# -- extensions subcommands --

@extensions_app.command("list")
def extensions_list() -> None:
    """Extensions are not yet implemented."""
    console.print("[yellow]Extensions are not yet implemented; no extensions are loaded.[/yellow]")
    raise typer.Exit(1)


@app.command("self-update")
def self_update() -> None:
    """Update from GitHub on the installed beta or stable channel."""
    from invoq.lifecycle import self_update as update_installation

    try:
        update_installation()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        console.print(f"Update failed: {exc}", markup=False)
        console.print("If an update was interrupted, rerun this repository's installer.")
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
