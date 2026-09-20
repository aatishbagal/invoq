# invoq - Development Prompts

> Phased prompts for Claude Code and Gemini CLI
> Use these prompts sequentially to build the project

---

## How to Use This Document

1. Treat the cross-platform roadmap below as the current source of planning
   truth.
2. The original numbered prompts are retained as implementation history; do
   not execute a legacy prompt unchanged when it conflicts with the current
   platform or security requirements.
3. Complete the acceptance criteria for a milestone before advancing it.
4. Test every changed capability on each supported platform before release.
5. **Update version in pyproject.toml only when the corresponding current
   milestone is complete.**

---

## Current Product Direction

invoq is an open-source terminal assistant targeting **Linux, macOS, and
Windows**. Linux is the current implementation base; macOS and Windows are
active development targets, not released support yet. The first public release
must not describe a platform as supported until its command execution,
confirmation, local storage, installation, update, uninstall, and integration
tests meet the same security bar as the other supported platforms.

The execution model must be platform-aware. Linux and macOS use distinct POSIX
shell adapters; Windows uses a PowerShell adapter. Command strings, blocked
patterns, paths, shell hooks, and installers must never be copied between
platforms as if they were equivalent.

## Cross-Platform Release Roadmap

| Milestone | Target Version | Deliverable | Linux | macOS | Windows |
|---|---:|---|---|---|---|
| Platform contract | 0.13.0 | Platform capability model, native data/config paths, shell selection, and platform test fixtures | Implement | Implement | Implement |
| Secure execution redesign | 0.14.0 | Structured, fail-closed command policy; no raw shell bypasses; per-platform confirmation | Implement | Implement | Implement |
| Execution adapters | 0.15.0 | Independently tested Linux shell, macOS shell, and PowerShell execution adapters | Implement | Implement | Implement |
| MCP boundary and schemas | 0.16.0 | Typed tools, policy-owned dispatch, audit logging, and no extension bypass path | Implement | Implement | Implement |
| Core workflows | 0.17.0 | Ask, debug, explain, history, and confirmation flows with capability-aware UX | Implement | Implement | Implement |
| Extensions and shell integration | 0.18.0 | Isolated extensions plus Bash/Zsh and PowerShell integration where safe | Implement | Implement | Implement |
| Quality and documentation | 0.19.0 | Three-platform CI, security regression suite, documentation, and accessibility review | Implement | Implement | Implement |
| Packaging and release candidate | 0.20.0 | Clean install/update/uninstall flows and release artifacts for every platform | Implement | Implement | Implement |
| First public release | 1.0.0 | Supported Linux, macOS, and Windows release | Supported | Supported | Supported |

### Cross-Platform Acceptance Rules

- A feature is incomplete until it is implemented and tested on all three
  target platforms, or is explicitly unavailable with a safe, documented
  platform-specific reason approved before merge.
- Platform adapters own command construction and execution. Higher-level MCP,
  validator, and UI code must use capabilities rather than inspect operating
  system names directly.
- Windows support means a tested PowerShell execution path. `cmd.exe` is not a
  substitute for PowerShell and requires its own future adapter if supported.
- Security policy is per platform: a Linux block pattern is not evidence that
  an equivalent PowerShell or macOS operation is protected.
- CI must include native Linux, macOS, and Windows runners before 1.0.0.

## Historical Version Roadmap

The table below records the original Linux-first college-project plan through
1.0.0. It is retained for traceability and does not override the current
cross-platform roadmap.

| Prompt | Version | Milestone |
|--------|---------|-----------|
| 1.1 | 0.1.0 | Project structure |
| 1.2 | 0.2.0 | Configuration |
| 1.3 | 0.3.0 | LLM interface |
| 1.4 | 0.4.0 | Model selection |
| 2.1 | 0.5.0 | Command validation |
| 2.2 | 0.6.0 | Safe executor |
| 2.3 | 0.7.0 | History tracking |
| 3.1 | 0.8.0 | MCP server |
| 3.2 | 0.9.0 | MCP tool schemas |
| 3.3 | 0.10.0 | MCP client |
| 3.4 | 0.11.0 | Confirmation flow |
| 4.1 | 0.12.0 | System prompts |
| 4.2 | 0.13.0 | Command generator |
| 4.3 | 0.14.0 | Debug feature |
| 4.4 | 0.15.0 | Explain feature |
| 5.1 | 0.16.0 | CLI commands |
| 5.2 | 0.17.0 | Config CLI |
| 5.3 | 0.18.0 | Confirmation UI |
| 6.1 | 0.19.0 | Extension framework |
| 6.2 | 0.20.0 | Git extension |
| 6.3 | 0.21.0 | Extensions CLI |
| 7.1 | 0.22.0 | Shell hooks |
| 7.2 | 0.23.0 | Shell CLI |
| 8.1 | 0.24.0 | Error handling |
| 8.2 | 0.25.0 | Version management |
| 8.3 | 0.26.0 | Testing |
| 8.4 | 0.27.0 | Documentation |
| 8.5 | **1.0.0** | **Release** |

---

## Master Rules (Apply to ALL Prompts)

**Include these rules at the start of every prompt:**

```
RULES - Follow these strictly for all code generation:

1. CODE STYLE
   - No emojis anywhere in code
   - No unnecessary comments - only basic label comments where needed
   - Keep code clean and self-documenting

2. FILE MANAGEMENT
   - NEVER delete any files - move to a `deprecated/` folder instead
   - Keep file structure modular with appropriate naming
   - No unnecessary function/class name changes for existing code unless required

3. TERMINAL SAFETY
   - Do not run any destructive commands (rm, drop, delete, etc.)
   - If destructive action needed, ask user to run it manually and share output

4. VERSION MANAGEMENT
   - Single source of truth: version defined ONLY in pyproject.toml
   - Use semantic versioning: MAJOR.MINOR.PATCH (e.g., 1.0.0)
   - Access version programmatically via importlib.metadata
   - Update version after completing each prompt

5. PLATFORM PARITY
   - Linux, macOS, and Windows are equal product targets.
   - Do not add OS checks throughout feature code. Define or extend a
     platform adapter and capability contract instead.
   - Do not translate shell syntax between platforms with string replacement.
     Each adapter must construct, validate, and execute its native operations.
   - A feature must have tests for all supported platforms before it is marked
     complete. Unsupported behavior must fail closed with a clear message.
```

---

## Cross-Platform Implementation Contract

The current roadmap requires these design decisions before any existing
Linux-first execution code is extended:

1. Define a platform interface for capabilities, native config/data locations,
   command representation, execution, confirmation display, and shell
   integration.
2. Keep a platform-neutral operation model above the adapters. An operation is
   validated before an adapter renders or invokes its native command; adapters
   must not accept arbitrary raw shell text from the LLM.
3. Implement separate policy fixtures for POSIX shells and PowerShell. Include
   positive, rejected, escaped, nested, redirected, and state-changing cases.
4. Add native integration tests on Linux, macOS, and Windows for every adapter
   and run them in CI. Do not use one platform's shell to simulate another.
5. Treat installer, updater, uninstaller, history, shell integration, and
   documentation as platform features. Each must reach parity before 1.0.0.

## Archived Linux-First Detailed Prompts

The prompts below document the original college-project implementation plan.
They are useful as historical context only. Any work derived from them must be
rewritten to satisfy the current product direction, cross-platform roadmap,
and security acceptance rules above.

## Phase 1: Project Foundation

### Prompt 1.1 - Project Structure
**Version after completion: 0.1.0**

```
Create a Python project structure for a CLI tool called "invoq".

Requirements:
- Python 3.11+ with pyproject.toml (use setuptools)
- Main package in src/invoq/
- Entry point: src/invoq/main.py
- CLI framework: Typer
- Dependencies: typer, rich, pyyaml, anyio

Structure needed:
src/invoq/
  __init__.py
  main.py         # CLI entry point with Typer app
  config.py       # Configuration management
  
config/
  default.yaml    # Default configuration template
  
tests/
  __init__.py
  
pyproject.toml
README.md

In main.py, create a basic Typer app with these placeholder commands:
- ask: takes a prompt string argument
- debug: no arguments
- explain: takes a command string argument
- config: subcommand group (placeholder)
- extensions: subcommand group (placeholder)

Use Rich for console output. Add --version flag.

Set version = "0.1.0" in pyproject.toml.
```

### Prompt 1.2 - Configuration System
**Version after completion: 0.2.0**

```
In the existing project, implement the configuration system in src/invoq/config.py

Requirements:
1. Config file location: ~/.config/invoq/config.yaml
2. Create config directory if it doesn't exist
3. Load default config from package, then override with user config

Config structure (as Python dataclass or Pydantic model):
- llm:
    backend: "ollama"  # ollama, llamacpp, or llamafile
    model: "auto"      # auto-detect based on RAM, or specific model name
    api_url: "http://localhost:11434"
- execution:
    require_confirmation: true
    show_command_explanation: true
    allow_sudo_bypass: true
- extensions:
    enabled: ["git"]   # list of enabled extension names

Functions needed:
- load_config() -> Config
- save_config(config: Config) -> None
- get_config_path() -> Path
- ensure_config_dir() -> Path

Include error handling for malformed YAML.

Update version to "0.2.0" in pyproject.toml.
```

### Prompt 1.3 - LLM Interface (Ollama)
**Version after completion: 0.3.0**

```
Create src/invoq/llm/ollama.py for Ollama integration.

Requirements:
1. Use ollama-python package (add to dependencies)
2. Async interface for streaming responses

Implement class OllamaClient:
  - __init__(self, model: str, api_url: str)
  - async def generate(self, prompt: str, system_prompt: str = None) -> str
  - async def generate_stream(self, prompt: str, system_prompt: str = None) -> AsyncIterator[str]
  - async def check_connection(self) -> bool
  - async def list_models(self) -> list[str]
  - async def get_model_info(self, model: str) -> dict

Also create src/invoq/llm/__init__.py with:
- Abstract base class LLMClient defining the interface
- Factory function get_llm_client(config: Config) -> LLMClient

Handle connection errors gracefully with helpful error messages.

Update version to "0.3.0" in pyproject.toml.
```

### Prompt 1.4 - Auto Model Selection
**Version after completion: 0.4.0**

```
Create src/invoq/llm/model_selector.py

Requirements:
1. Detect available system RAM using psutil (add to dependencies)
2. Select appropriate model based on RAM

Model tiers:
- Under 4GB: Error - insufficient RAM
- 4-6GB: "qwen2.5-coder:1.5b" or "phi3:mini"
- 6-8GB: "qwen2.5-coder:7b-q4_0"
- 8GB+: "qwen2.5-coder:7b"

Functions:
- get_available_ram_gb() -> float
- get_recommended_model() -> str
- check_model_available(model: str) -> bool  # check if Ollama has it
- suggest_model_download() -> str  # returns ollama pull command

Integrate with config - if config.llm.model is "auto", use auto-selection.

Update version to "0.4.0" in pyproject.toml.
```

---

## Phase 2: Command Validation & Security

### Prompt 2.1 - Command Allowlist System
**Version after completion: 0.5.0**

```
Create src/invoq/core/validator.py

This is the SECURITY CRITICAL component. Implement allowlist-based command validation.

Requirements:
1. Commands NOT in allowlist are BLOCKED by default
2. Check base command AND dangerous patterns

Data structures:
- SAFE_COMMANDS: set of always-allowed commands (ls, pwd, cat, grep, find, echo, head, tail, wc, sort, uniq, diff, file, which, whoami, date, cal, env)
- CONFIRM_COMMANDS: set of commands requiring confirmation (git, docker, npm, pip, cargo, make, gcc, g++, python, node, curl, wget, tar, gzip, unzip, cp, mv, mkdir, touch, chmod, chown)
- BLOCKED_PATTERNS: list of regex patterns that are NEVER allowed:
  - rm with -r or -f flags
  - dd command
  - mkfs.* commands
  - chmod 777
  - > /dev/sd[a-z]
  - fork bombs
  - shred command

Class CommandValidator:
  - validate(command: str) -> ValidationResult
  - ValidationResult: dataclass with (allowed: bool, tier: str, reason: str, commands_used: list[str])
  - extract_base_commands(command: str) -> list[str]  # handles pipes, &&, ||, etc.
  - check_dangerous_patterns(command: str) -> tuple[bool, str]

Handle edge cases: subshells, command substitution, quoted strings.

Update version to "0.5.0" in pyproject.toml.
```

### Prompt 2.2 - Safe Command Executor
**Version after completion: 0.6.0**

```
Create src/invoq/core/executor.py

Implements safe subprocess execution with user confirmation.

Requirements:
1. Always show full command before execution
2. Require explicit confirmation (unless in safe tier)
3. Support y/n/e (yes/no/edit) responses
4. Capture stdout and stderr separately
5. Handle timeouts

Class SafeExecutor:
  - __init__(self, validator: CommandValidator, config: Config)
  - async def execute(self, command: str, skip_confirmation: bool = False) -> ExecutionResult
  - async def execute_script(self, script: str, skip_confirmation: bool = False) -> ExecutionResult
  - prompt_confirmation(self, command: str, tier: str) -> ConfirmationResult
  
ExecutionResult dataclass:
  - success: bool
  - exit_code: int
  - stdout: str
  - stderr: str
  - command: str
  - duration_ms: int

ConfirmationResult: enum (YES, NO, EDIT)

For EDIT option: save command to temp file, open in $EDITOR, read back modified command.

Use Rich for formatted confirmation prompts.

Update version to "0.6.0" in pyproject.toml.
```

### Prompt 2.3 - Command History Tracking
**Version after completion: 0.7.0**

```
Create src/invoq/core/history.py

Track commands executed through the tool for debugging.

Requirements:
1. Store in ~/.local/share/invoq/history.json
2. Keep last 100 commands (configurable)
3. Record: command, timestamp, exit_code, stderr (truncated), cwd

Class CommandHistory:
  - __init__(self, max_entries: int = 100)
  - add(self, command: str, exit_code: int, stderr: str, cwd: str) -> None
  - get_last(self) -> HistoryEntry | None
  - get_last_failed(self) -> HistoryEntry | None
  - get_recent(self, n: int = 10) -> list[HistoryEntry]
  - clear(self) -> None

HistoryEntry dataclass:
  - command: str
  - timestamp: datetime
  - exit_code: int
  - stderr: str (max 500 chars)
  - cwd: str
  
Ensure thread-safe file access.

Update version to "0.7.0" in pyproject.toml.
```

---

## Phase 3: MCP Server Implementation

### Prompt 3.1 - MCP Core Server
**Version after completion: 0.8.0**

```
Create the MCP (Model Context Protocol) server for invoq.

Add dependency: mcp (Anthropic's official MCP SDK)

Create src/invoq/mcp/server.py

Requirements:
1. Implement MCP server that exposes shell tools to the LLM
2. Tools are the ONLY way the LLM can execute commands
3. Each tool has typed input schemas for validation

Implement InvoqMCPServer class:
  - Uses the mcp Python SDK
  - Registers tools with the server
  - Handles tool calls from LLM

Core tools to register:

1. execute_command
   - description: "Execute a shell command"
   - input_schema: { command: str, working_dir: str (optional) }
   - Validates command through CommandValidator before execution
   - Returns: { stdout: str, stderr: str, exit_code: int }

2. execute_script  
   - description: "Execute a multi-line bash script"
   - input_schema: { script: str, working_dir: str (optional) }
   - Validates ALL commands in script
   - Returns: { stdout: str, stderr: str, exit_code: int }

3. read_file
   - description: "Read contents of a file"
   - input_schema: { path: str, max_lines: int (optional) }
   - Returns: { content: str, lines: int }

4. list_directory
   - description: "List directory contents"
   - input_schema: { path: str, show_hidden: bool }
   - Returns: { entries: list[{name, type, size}] }

5. get_system_info
   - description: "Get system information"
   - input_schema: {}
   - Returns: { os, shell, cwd, user, kernel }

Security architecture:
- LLM can ONLY call these registered tools
- Each tool internally uses CommandValidator
- Blocked commands return error, not execution
- All tool calls logged for audit

Example MCP server setup:
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("invoq")

@server.tool()
async def execute_command(command: str, working_dir: str = None) -> str:
    # Validate and execute
    ...

Update version to "0.8.0" in pyproject.toml.
```

### Prompt 3.2 - MCP Tool Schemas
**Version after completion: 0.9.0**

```
Create src/invoq/mcp/tools.py

Define all MCP tool schemas with proper typing and validation.

Requirements:
1. Use Pydantic models for input/output schemas
2. Each tool has clear description for LLM understanding
3. Include constraints in schema (max lengths, allowed values, etc.)

Tool definitions:

class ExecuteCommandInput(BaseModel):
    command: str = Field(..., description="Shell command to execute", max_length=1000)
    working_dir: str | None = Field(None, description="Working directory")

class ExecuteCommandOutput(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int

class ReadFileInput(BaseModel):
    path: str = Field(..., description="Absolute or relative file path")
    max_lines: int = Field(100, description="Maximum lines to read", le=1000)

class ListDirectoryInput(BaseModel):
    path: str = Field(".", description="Directory path")
    show_hidden: bool = Field(False, description="Include hidden files")

Also create tool metadata:

TOOL_DEFINITIONS = [
    {
        "name": "execute_command",
        "description": "Execute a shell command. Only allowed commands will run. Dangerous commands like rm -rf are blocked.",
        "input_schema": ExecuteCommandInput.model_json_schema(),
    },
    # ... etc
]

This metadata is sent to the LLM so it knows what tools are available.

Update version to "0.9.0" in pyproject.toml.
```

### Prompt 3.3 - MCP Client Integration
**Version after completion: 0.10.0**

```
Create src/invoq/mcp/client.py

Integrate MCP with the Ollama LLM client for tool calling.

Requirements:
1. Send tool definitions to LLM with each request
2. Parse LLM responses for tool calls
3. Execute tool calls via MCP server
4. Return results to LLM for final response

Class MCPClient:
  - __init__(self, llm_client: LLMClient, mcp_server: InvoqMCPServer)
  - async def chat(self, user_message: str) -> ChatResult
  - async def chat_with_tools(self, user_message: str) -> ChatResult

ChatResult dataclass:
  - response: str  # Final text response
  - tool_calls: list[ToolCall]  # Tools that were called
  - tool_results: list[ToolResult]  # Results from tools

Conversation flow:
1. User: "list all python files"
2. Send to LLM with tool definitions
3. LLM responds: { "tool": "execute_command", "input": { "command": "find . -name '*.py'" } }
4. MCPClient calls MCP server's execute_command tool
5. Tool validates command (allowed), executes it
6. Result sent back to LLM
7. LLM formats final response for user

Handle:
- Multiple tool calls in sequence
- Tool call errors (show to user clearly)
- LLM deciding not to use tools (direct response)

Note: Ollama supports tool calling via the 'tools' parameter in the API.

Update version to "0.10.0" in pyproject.toml.
```

### Prompt 3.4 - MCP Confirmation Flow
**Version after completion: 0.11.0**

```
Create src/invoq/mcp/confirmation.py

Implement user confirmation as part of the MCP tool execution flow.

Requirements:
1. Tools in CONFIRM tier require user approval before execution
2. Show command clearly with Rich formatting
3. Support yes/no/edit options
4. Audit log all confirmations

Class ConfirmationHandler:
  - __init__(self, config: Config)
  - async def request_confirmation(self, tool_call: ToolCall) -> ConfirmationResult
  - format_tool_call_display(self, tool_call: ToolCall) -> str

ConfirmationResult: enum (APPROVED, DENIED, EDITED)

Integration with MCP server:

@server.tool()
async def execute_command(command: str, working_dir: str = None) -> str:
    validation = validator.validate(command)
    
    if not validation.allowed:
        return f"BLOCKED: {validation.reason}"
    
    if validation.tier == "confirm":
        result = await confirmation_handler.request_confirmation(
            ToolCall(name="execute_command", input={"command": command})
        )
        if result == ConfirmationResult.DENIED:
            return "Command cancelled by user"
        if result == ConfirmationResult.EDITED:
            command = result.edited_command
    
    # Execute command
    ...

Display format (using Rich):
+-- Tool Call: execute_command ---------------------+
| Command: git push origin main                     |
| Tier: CONFIRM (requires approval)                 |
| Working Dir: /home/user/project                   |
+---------------------------------------------------+
Execute? [y]es / [n]o / [e]dit: 

Update version to "0.11.0" in pyproject.toml.
```

---

## Phase 4: Core AI Features

### Prompt 4.1 - System Prompts
**Version after completion: 0.12.0**

```
Create src/invoq/prompts/system_prompts.py

Define system prompts for different modes.

Requirements:
1. Prompts should be clear, concise, and focused
2. Include OS/shell context dynamically
3. Emphasize tool usage for all command execution
4. Never generate commands without using tools

Create these prompt templates (as string constants or functions):

COMMAND_GENERATION_PROMPT:
"""
You are a Linux command line expert assistant. You help users by executing shell commands.

IMPORTANT RULES:
1. You MUST use the execute_command tool to run any commands
2. Never just show a command - always execute it via the tool
3. If a command is blocked, explain why and suggest alternatives
4. For multi-step tasks, use tools sequentially

Available tools:
- execute_command: Run a shell command
- execute_script: Run a multi-line bash script
- read_file: Read file contents
- list_directory: List directory contents
- get_system_info: Get OS/shell information

Current context:
- Shell: {shell}
- OS: {os_info}
- Working directory: {cwd}
- User: {user}

Respond concisely. Execute commands via tools, then explain results.
"""

DEBUG_PROMPT:
"""
You are a Linux debugging expert. A command has failed and you need to diagnose and fix it.

Failed command: {command}
Exit code: {exit_code}
Error output: {stderr}
Working directory: {cwd}

Use the available tools to:
1. Investigate the cause (read files, list directories, check system info)
2. Suggest and execute a fix using execute_command
3. Explain what went wrong and how the fix works

Always use tools - never suggest commands without executing them.
"""

EXPLAIN_PROMPT:
"""
You are a Linux teacher. Explain what the following command does in plain language.

Command: {command}

Break down:
1. Each part of the command
2. What options/flags do
3. Data flow for pipes
4. Any potential risks

You may use get_system_info or read_file tools if needed for context.
"""

Helper function:
- get_system_context() -> dict  # returns shell, os, kernel, cwd, user

Update version to "0.12.0" in pyproject.toml.
```

### Prompt 4.2 - Command Generation Pipeline
**Version after completion: 0.13.0**

```
Create src/invoq/core/generator.py

Main logic for natural language to command conversion using MCP.

Requirements:
1. Take user prompt, send to LLM with tools
2. LLM uses execute_command tool to run commands
3. Handle tool results and format response
4. Support multi-turn for complex tasks

Class CommandGenerator:
  - __init__(self, mcp_client: MCPClient, config: Config)
  - async def generate(self, user_prompt: str) -> GenerationResult

GenerationResult dataclass:
  - response: str  # LLM's final response
  - commands_executed: list[ExecutedCommand]
  - success: bool

ExecutedCommand dataclass:
  - command: str
  - exit_code: int
  - stdout: str
  - stderr: str
  - was_blocked: bool
  - block_reason: str | None

Logic flow:
1. Build system prompt with context
2. Send user prompt + tools to LLM
3. LLM decides to call execute_command tool
4. MCP server validates and executes (with confirmation if needed)
5. Result sent back to LLM
6. LLM may call more tools or provide final response
7. Return formatted result to user

Handle edge cases:
- LLM tries to call non-existent tool
- Tool execution timeout
- Multiple commands in sequence
- User cancels during confirmation

Update version to "0.13.0" in pyproject.toml.
```

### Prompt 4.3 - Debug Feature
**Version after completion: 0.14.0**

```
Create src/invoq/core/debugger.py

Implements the "debug last command" feature using MCP tools.

Requirements:
1. Get last failed command from history
2. Send to LLM with debug prompt and tools
3. LLM investigates using tools and suggests fix
4. Execute fix via tools with user confirmation

Class CommandDebugger:
  - __init__(self, mcp_client: MCPClient, history: CommandHistory)
  - async def debug_last(self) -> DebugResult
  - async def debug_command(self, command: str, exit_code: int, stderr: str) -> DebugResult

DebugResult dataclass:
  - original_command: str
  - diagnosis: str  # LLM's explanation of what went wrong
  - fix_attempted: bool
  - fix_command: str | None
  - fix_result: ExecutionResult | None

Debug flow:
1. Get last failed command from history
2. Build debug prompt with error context
3. LLM uses tools to investigate:
   - read_file to check configs
   - list_directory to verify paths
   - get_system_info for environment
4. LLM proposes fix via execute_command tool
5. User confirms or denies fix
6. Return full debug report

Update version to "0.14.0" in pyproject.toml.
```

### Prompt 4.4 - Explain Feature
**Version after completion: 0.15.0**

```
Create src/invoq/core/explainer.py

Explains what a command does in plain language.

Requirements:
1. Send command to LLM with explain prompt
2. LLM breaks down each component
3. Optionally use tools for context (man pages, file checks)
4. Warn about dangerous operations

Class CommandExplainer:
  - __init__(self, mcp_client: MCPClient, validator: CommandValidator)
  - async def explain(self, command: str) -> ExplanationResult

ExplanationResult dataclass:
  - command: str
  - summary: str  # One-line summary
  - breakdown: list[ComponentExplanation]
  - warnings: list[str]  # Safety concerns
  - tier: str  # safe/confirm/blocked

ComponentExplanation dataclass:
  - component: str  # e.g., "grep -r 'pattern'"
  - explanation: str
  - purpose: str  # What it does in the pipeline

Add warnings for:
- Commands in CONFIRM tier
- Operations that modify files
- Network operations
- Elevated privilege requirements
- Commands close to blocked patterns

Update version to "0.15.0" in pyproject.toml.
```

---

## Phase 5: CLI Integration

### Prompt 5.1 - Main CLI Commands
**Version after completion: 0.16.0**

```
Update src/invoq/main.py to implement all CLI commands.

Wire up all the components created in previous phases.

Commands to implement:

@app.command()
async def ask(prompt: str, execute: bool = False):
    """Generate and execute command from natural language."""
    # 1. Load config
    # 2. Initialize MCP client
    # 3. Send prompt to LLM with tools
    # 4. LLM uses tools to execute commands
    # 5. Show formatted result

@app.command()
async def debug():
    """Debug the last failed command."""
    # 1. Get last failed from history
    # 2. If none, show helpful message
    # 3. Run debugger with MCP
    # 4. Show diagnosis and fix attempt

@app.command()
async def explain(command: str):
    """Explain what a command does."""
    # 1. Run explainer
    # 2. Show formatted breakdown with Rich

@app.command()
def history(count: int = 10):
    """Show recent command history."""
    # Show table with Rich

Use Rich for all output:
- Panels for command/response display
- Tables for history and tool calls
- Syntax highlighting for code
- Live progress during LLM calls

Handle Ctrl+C gracefully - cancel ongoing operations.

Update version to "0.16.0" in pyproject.toml.
```

### Prompt 5.2 - Config CLI Subcommands
**Version after completion: 0.17.0**

```
Create src/invoq/cli/config_commands.py

Implement config management subcommands.

@config_app.command("show")
def config_show():
    """Show current configuration."""
    # Pretty print config with Rich

@config_app.command("edit")
def config_edit():
    """Open config in editor."""
    # Open config file in $EDITOR

@config_app.command("reset")
def config_reset():
    """Reset config to defaults."""
    # Confirm, then reset

@config_app.command("set")
def config_set(key: str, value: str):
    """Set a config value."""
    # e.g., config set llm.model qwen2.5-coder:7b
    # Parse dotted key path, update config, save

@config_app.command("get")
def config_get(key: str):
    """Get a config value."""

Register this as subcommand group in main.py.

Update version to "0.17.0" in pyproject.toml.
```

### Prompt 5.3 - Interactive Confirmation UI
**Version after completion: 0.18.0**

```
Create src/invoq/ui/confirmation.py

Rich-based confirmation UI for command execution.

Requirements:
1. Show command in syntax-highlighted panel
2. Show tool call details and tier
3. Show any warnings
4. Present options: [y]es / [n]o / [e]dit / [?]help

Function confirm_tool_execution(
    tool_call: ToolCall,
    validation: ValidationResult,
) -> ConfirmationChoice:

ConfirmationChoice: enum (YES, NO, EDIT, HELP)

Display format:
+-- Tool: execute_command --------------------------+
|                                                   |
|  git push origin main --force                     |
|                                                   |
+---------------------------------------------------+
| Tier: CONFIRM                                     |
| Commands: git (allowed)                           |
| Warning: --force overwrites remote history        |
+---------------------------------------------------+
Execute? [y]es / [n]o / [e]dit / [?]help: 

For EDIT choice:
- Save to temp file
- Open in $EDITOR
- Read back and re-validate
- Show diff if changed
- Confirm again

Use Rich components:
- Panel for display
- Syntax for code highlighting
- Table for tool details
- Prompt for input

Update version to "0.18.0" in pyproject.toml.
```

---

## Phase 6: Extension System

### Prompt 6.1 - Extension Base Framework
**Version after completion: 0.19.0**

```
Create src/invoq/extensions/base.py

Define the extension system using MCP tools.

Requirements:
1. Extensions add new MCP tools
2. Each extension declares its allowed commands
3. Extensions can be enabled/disabled
4. Extensions are loaded as additional MCP tool providers

@dataclass
class ExtensionMetadata:
    name: str
    version: str
    description: str
    author: str
    requires_binary: str | None  # e.g., "git", "docker"

class Extension(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ExtensionMetadata: ...
    
    @abstractmethod
    def get_tools(self) -> list[Tool]:
        """Return MCP tools provided by this extension."""
    
    @abstractmethod
    def get_allowed_commands(self) -> set[str]:
        """Commands this extension adds to the allowlist."""
    
    def is_available(self) -> bool:
        """Check if required binary exists."""

Extension registry:

class ExtensionRegistry:
    - discover_extensions() -> dict[str, Type[Extension]]
    - load_extension(name: str) -> Extension | None
    - get_enabled_extensions() -> list[Extension]
    - enable(name: str) -> bool
    - disable(name: str) -> bool
    - get_all_tools() -> list[Tool]  # Combined tools from all extensions
    - get_all_allowed_commands() -> set[str]  # Combined allowlist

Update version to "0.19.0" in pyproject.toml.
```

### Prompt 6.2 - Git Extension
**Version after completion: 0.20.0**

```
Create src/invoq/extensions/git/extension.py

Built-in Git extension providing git-specific MCP tools.

Requirements:
1. Add 'git' to allowed commands
2. Provide git-specific tools beyond basic execute_command
3. Include helpful git operations

GitExtension(Extension):
    metadata: name="git", requires_binary="git"
    
MCP Tools to implement:

1. git_status
   - description: "Get current git repository status"
   - input_schema: { path: str (optional) }
   - Runs: git status --porcelain -b
   - Returns: { branch, ahead, behind, staged, unstaged, untracked }

2. git_diff
   - description: "Show git diff"
   - input_schema: { staged: bool, file: str (optional) }
   - Returns: { diff: str, files_changed: int }

3. git_log
   - description: "Show recent commits"
   - input_schema: { count: int, oneline: bool }
   - Returns: { commits: list[{hash, author, message, date}] }

4. git_commit_suggest
   - description: "Analyze staged changes and suggest commit message"
   - Uses LLM to generate commit message from diff
   - Returns: { suggested_message: str, files: list[str] }

All tools should:
- Validate we're in a git repo
- Handle errors gracefully
- Work from any subdirectory

Update version to "0.20.0" in pyproject.toml.
```

### Prompt 6.3 - Extensions CLI
**Version after completion: 0.21.0**

```
Create src/invoq/cli/extension_commands.py

CLI commands for managing extensions.

@ext_app.command("list")
def ext_list():
    """List all available extensions."""
    # Show table: name, description, status, requires, tools provided

@ext_app.command("enable")
def ext_enable(name: str):
    """Enable an extension."""
    # Check if available (binary exists)
    # Add to enabled list in config
    # Reload MCP server with new tools

@ext_app.command("disable")
def ext_disable(name: str):
    """Disable an extension."""

@ext_app.command("info")
def ext_info(name: str):
    """Show detailed info about an extension."""
    # Show metadata
    # List all MCP tools provided
    # Show commands added to allowlist

Update main.py to:
1. Load enabled extensions on startup
2. Register extension tools with MCP server
3. Merge extension allowlists with core allowlist

Update version to "0.21.0" in pyproject.toml.
```

---

## Phase 7: Shell Integration

### Prompt 7.1 - Shell Hooks
**Version after completion: 0.22.0**

```
Create src/invoq/shell/hooks.py

Generate shell hook scripts for bash and zsh.

Requirements:
1. Capture failed commands automatically
2. Store in format readable by our history system
3. Non-intrusive - don't break existing shell behavior

Generate two hook scripts:

bash_hook() -> str:
    """Generate bash hook script content."""
    # Trap DEBUG to capture commands
    # Trap ERR to capture failures
    # Write to ~/.local/share/invoq/shell_failures.log

zsh_hook() -> str:
    """Generate zsh hook script content."""
    # Use precmd and preexec hooks
    # Similar logging

Hook data format (one JSON per line):
{
    "command": "...",
    "exit_code": 1,
    "stderr_file": "/tmp/...",
    "cwd": "...",
    "timestamp": "..."
}

Also create installer:

install_shell_hooks() -> None:
    """Add hooks to user's shell rc file."""
    # Detect shell (SHELL env var)
    # Generate appropriate hook
    # Save to ~/.config/invoq/shell_hook.sh
    # Add source line to .bashrc/.zshrc (if not present)
    # Warn user to restart shell

uninstall_shell_hooks() -> None:
    """Remove hooks from rc files."""

Update version to "0.22.0" in pyproject.toml.
```

### Prompt 7.2 - Shell Integration CLI
**Version after completion: 0.23.0**

```
Create src/invoq/cli/shell_commands.py

CLI commands for shell integration.

@shell_app.command("install")
def shell_install():
    """Install shell hooks for automatic error capture."""
    # Show what will be added
    # Ask for confirmation
    # Install hooks
    # Show "restart your shell" message

@shell_app.command("uninstall")
def shell_uninstall():
    """Remove shell hooks."""

@shell_app.command("status")
def shell_status():
    """Check if shell hooks are installed and working."""
    # Check if hook file exists
    # Check if sourced in rc file
    # Check if log file is being written to

Integrate with debug command:
- If shell hooks installed, debug can access richer error info
- If not installed, suggest installing for better debugging

Update version to "0.23.0" in pyproject.toml.
```

---

## Phase 8: Polish & Packaging

### Prompt 8.1 - Error Handling & Edge Cases
**Version after completion: 0.24.0**

```
Review and improve error handling across the project.

Tasks:
1. Create src/invoq/exceptions.py with custom exceptions:
   - ConfigError
   - LLMConnectionError
   - LLMResponseError
   - ValidationError
   - ExecutionError
   - ExtensionError
   - MCPError

2. Update all modules to use these exceptions

3. Create error handler in main.py:
   - Catch all custom exceptions
   - Display user-friendly error messages with Rich
   - Suggest solutions where possible
   - Show --verbose flag hint for stack traces

4. Handle specific edge cases:
   - Ollama not running: detect and show install/start instructions
   - Model not downloaded: show ollama pull command
   - MCP server fails to start: clear error message
   - Tool call timeout: graceful handling
   - Empty LLM response: retry or show error
   - Malformed LLM response: attempt to parse anyway

5. Add --verbose flag to main app for debug output

Update version to "0.24.0" in pyproject.toml.
```

### Prompt 8.2 - Version Management
**Version after completion: 0.25.0**

```
Set up centralized version management for invoq.

Requirements:
1. Single source of truth in pyproject.toml
2. Version accessible programmatically throughout codebase
3. CLI --version flag shows current version
4. Simple script to bump versions

Implementation:

1. In pyproject.toml, ensure version is defined:
   [project]
   name = "invoq"
   version = "0.25.0"

2. Create src/invoq/_version.py:
   from importlib.metadata import version, PackageNotFoundError
   
   try:
       __version__ = version("invoq")
   except PackageNotFoundError:
       __version__ = "0.0.0-dev"

3. In src/invoq/__init__.py:
   from invoq._version import __version__

4. Update main.py to use version:
   from invoq import __version__
   
   @app.callback(invoke_without_command=True)
   def main(version: bool = typer.Option(False, "--version", "-V")):
       if version:
           console.print(f"invoq {__version__}")
           raise typer.Exit()

5. Create scripts/bump_version.py:
   """
   Usage: python scripts/bump_version.py [major|minor|patch]
   
   Bumps version in pyproject.toml following semver.
   """
   import sys
   import re
   from pathlib import Path
   
   def bump_version(part: str) -> None:
       pyproject = Path("pyproject.toml")
       content = pyproject.read_text()
       
       match = re.search(r'version = "(\d+)\.(\d+)\.(\d+)"', content)
       if not match:
           print("Could not find version in pyproject.toml")
           sys.exit(1)
       
       major, minor, patch = map(int, match.groups())
       
       if part == "major":
           major += 1
           minor = 0
           patch = 0
       elif part == "minor":
           minor += 1
           patch = 0
       elif part == "patch":
           patch += 1
       else:
           print(f"Unknown part: {part}. Use major, minor, or patch")
           sys.exit(1)
       
       new_version = f"{major}.{minor}.{patch}"
       new_content = re.sub(
           r'version = "\d+\.\d+\.\d+"',
           f'version = "{new_version}"',
           content
       )
       
       pyproject.write_text(new_content)
       print(f"Bumped version to {new_version}")
       print(f"Don't forget: git tag v{new_version}")
   
   if __name__ == "__main__":
       if len(sys.argv) != 2:
           print("Usage: python scripts/bump_version.py [major|minor|patch]")
           sys.exit(1)
       bump_version(sys.argv[1])

6. Add to pyproject.toml scripts section:
   [project.scripts]
   invoq = "invoq.main:app"

Version workflow:
- Development: version stays at current (e.g., 0.25.0)
- Ready for release: python scripts/bump_version.py patch
- Tag release: git tag v0.25.1 && git push --tags
- PyPI publish uses version from pyproject.toml automatically

Update version to "0.25.0" in pyproject.toml.
```

### Prompt 8.3 - Testing Setup
**Version after completion: 0.26.0**

```
Set up testing infrastructure.

Create tests/:
  conftest.py           # Pytest fixtures
  test_validator.py     # Test command validation
  test_executor.py      # Test execution (mocked)
  test_mcp_server.py    # Test MCP tools
  test_mcp_client.py    # Test LLM integration (mocked)
  test_config.py        # Test config loading/saving

Key test cases for validator:
- Safe commands pass
- Blocked patterns are caught
- Pipes and chains are parsed correctly
- Edge cases: quoted strings, subshells

Key test cases for MCP:
- Tool registration works
- Tool calls are validated
- Blocked commands return error
- Confirmation flow works

Fixtures needed:
- mock_llm_client: Returns predefined responses
- mock_mcp_server: MCP server with test tools
- temp_config: Temporary config directory
- mock_history: Temporary history file

Use pytest-asyncio for async tests.

Add to pyproject.toml:
[tool.pytest.ini_options]
asyncio_mode = "auto"

Update version to "0.26.0" in pyproject.toml.
```

### Prompt 8.4 - Documentation
**Version after completion: 0.27.0**

```
Create comprehensive documentation.

README.md:
- Project description and features
- Installation (pip, from source)
- Quick start guide
- Configuration reference
- MCP architecture overview
- Extension system overview
- Security model explanation
- Contributing guidelines

docs/:
  installation.md    # Detailed install for various distros
  configuration.md   # Full config reference
  usage.md          # Command reference with examples
  architecture.md   # MCP-based architecture deep dive
  extensions.md     # How to use and create extensions
  security.md       # Security model deep dive
  
Add docstrings to all public functions and classes.

Create man page (optional):
  man/invoq.1

Update version to "0.27.0" in pyproject.toml.
```

### Prompt 8.5 - Package Distribution
**Version after completion: 1.0.0 (RELEASE)**

```
Finalize packaging for distribution.

Update pyproject.toml:
- Add all dependencies with versions:
  - typer >= 0.9.0
  - rich >= 13.0.0
  - pyyaml >= 6.0
  - anyio >= 4.0.0
  - ollama >= 0.1.0
  - psutil >= 5.9.0
  - mcp >= 0.1.0  # Anthropic's MCP SDK
  - pydantic >= 2.0.0
- Add optional dependencies (dev, test)
- Configure entry points
- Add classifiers
- Add URLs (homepage, issues, docs)

Create:
- CHANGELOG.md (initial version)
- LICENSE (MIT recommended)
- .github/workflows/test.yml (basic CI)
- .github/workflows/publish.yml (PyPI publish on tag)

For native packages, create:
- packaging/PKGBUILD (Arch Linux AUR)
- packaging/debian/ (Debian/Ubuntu .deb)

Test installation:
- pip install -e .
- pip install . in clean venv
- Test all commands work after install

Update version to "1.0.0" in pyproject.toml - THIS IS THE RELEASE VERSION.
```

---

## Phase 9: Future Features (Post-Release)

### Prompt 9.1 - Internet Access via MCP Tool
**Version: 1.1.0 (post-release)**

```
NOTE: This is for v1.1.0. Skip for initial release.

Add optional web search capability as an MCP tool.

Create src/invoq/mcp/tools/web_search.py:
- New MCP tool: web_search
- input_schema: { query: str, max_results: int }
- Integrate with SearXNG or Tavily
- Returns: { results: list[{title, url, snippet}] }

Use cases:
- "What's the latest version of Node.js?"
- "How to fix [specific error] in [library]?"
- Look up man pages for obscure commands

Requirements:
- Disabled by default in config
- User must explicitly enable
- Privacy-focused (use SearXNG)
- Cache results to reduce queries
- Rate limiting

Update version to "1.1.0" in pyproject.toml.
```

---

## Quick Reference: File Structure

After completing all phases:

```
src/invoq/
    __init__.py
    main.py
    config.py
    exceptions.py
    _version.py
    core/
        __init__.py
        validator.py
        executor.py
        history.py
        generator.py
        debugger.py
        explainer.py
    llm/
        __init__.py
        ollama.py
        model_selector.py
    mcp/
        __init__.py
        server.py
        client.py
        tools.py
        confirmation.py
    prompts/
        __init__.py
        system_prompts.py
    extensions/
        __init__.py
        base.py
        registry.py
        git/
            __init__.py
            extension.py
    shell/
        __init__.py
        hooks.py
    cli/
        __init__.py
        config_commands.py
        extension_commands.py
        shell_commands.py
    ui/
        __init__.py
        confirmation.py
```

---

## Notes for AI Assistants

**IMPORTANT: Always prepend the Master Rules to every prompt before executing.**

Code Standards:
- Always use type hints
- Follow PEP 8 style
- Use async where appropriate (LLM calls, subprocess)
- Prefer composition over inheritance
- Keep functions focused and small
- Add logging with Python's logging module
- Handle errors at appropriate levels
- Use Rich for all user-facing output
- Security is critical - validate everything

File Management:
- Never delete files - move to deprecated/ folder
- No unnecessary renaming of existing functions/classes
- Keep modular structure with clear naming

Version Management:
- Single source of truth: pyproject.toml
- Use semantic versioning (MAJOR.MINOR.PATCH)
- Update version after each prompt completion
- 1.0.0 is the release version
