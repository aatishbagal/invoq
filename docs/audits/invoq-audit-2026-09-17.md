# invoq codebase audit — 2026-09-17

## 1. Summary

invoq has substantial implementation through the 0.12.1 CLI/MCP/explain milestone, with the core CLI, local Ollama integration, setup wizard, history, tool registry, and confirmation UI present. The highest evidenced phase is 0.12.1, but the security boundary is not safe to rely on: several entries labelled `SAFE` can write files or invoke arbitrary commands without confirmation, including bypasses of the documented blocked-command cases. Do not resume feature work or treat the tool as safe for LLM command execution until the Critical findings below are addressed and regression-tested.

## 2. Reference Documents

The required `invoq-specification.md`, `invoq-development-prompts.md`, and `invoq-literature-review.md` were not found in the repository root, `docs/`, or the requested planning locations; Git history also contains no paths matching those names. This is a process finding, not a reason to stop the audit. The assessment therefore uses the current source, tests, README, `pyproject.toml`, default configuration, and versioned commit history. The missing roadmap prevents an exact, prompt-by-prompt comparison.

## 3. Phase Completion Matrix

The expected versions and prompt names below are reconstructed from commit messages because the Version Roadmap table is absent.

| Phase | Prompt / evidenced capability | Expected Version | Status | Notes |
|---|---|---:|---|---|
| Foundation | Typer CLI, packaging, config scaffold | 0.1.0 | Done | Entrypoint, package metadata, config loader, and CLI groups exist. |
| Configuration and Ollama | Configuration plus local Ollama client | 0.3.0 | Done | `Config`, `OllamaClient`, and backend selection exist; only Ollama is supported. |
| Model selection | RAM/GPU-based model recommendation | 0.4.0 | Done | Selector and system detector are implemented. No tests cover either. |
| Security tiers | Allowlist validator and blocked patterns | 0.5.0 | Partial | Constants and validator exist, and canonical prohibited strings block; unsafe argument semantics make the model invalid as an enforcement boundary. |
| Setup | Setup wizard, detection, install/update scripts | 0.5.6 | Partial | Setup is wired to the CLI and saves configuration. No tests cover it; docs incorrectly imply it installs Ollama itself. |
| Executor | Validating shell/script executor and confirmation UI | 0.6.0 | Partial | Executor and tests exist, but it uses `create_subprocess_shell` after shallow parsing and exposes `skip_confirmation`. |
| History | Persistent command history | 0.7.0 (inferred) | Done | `CommandHistory` is integrated with executor and has focused tests. |
| MCP foundations | Types, registry, shell/filesystem tools, server | 0.8.0 | Partial | Built-in tools exist, but the registry has no policy gate for future executable tools or extensions. |
| Ask integration | Ollama tool-call execution and schemas | 0.9.0 | Partial | `ask` dispatches parsed calls. The `--execute` option is unused; tool calls execute regardless. Pydantic schemas are not used for dispatch validation. |
| MCP client | LLM/MCP tool loop | 0.10.0 | Done | `MCPClient` and bounded loop exist; there are no direct client tests. |
| Confirmation flow | MCP confirmation handler | 0.11.0 | Partial | Command and script confirmation code exists, but its safety depends on the insufficient validator. No tests exercise approval, denial, or edited commands through the server. |
| Explain and prompts | Explain command and system prompts | 0.12.0 | Partial | `explain` has an end-to-end path. `debug` is only a version display despite README and prompt support for debugging failures. |
| CLI polish | Help/version variants and README update | 0.12.1 | Done | `pyproject.toml` and the latest version commit both state 0.12.1. |

## 4. Version Consistency

`pyproject.toml` declares **0.12.1**. There is no `src/invoq/_version.py`; `src/invoq/__init__.py` reads installed package metadata and falls back to `0.1.0-dev` only when the package is not installed. The latest version-bearing commit is `8653b59` (`v0.12.1`), so the declared version is consistent with the observed repository history. It cannot be compared mechanically to the missing roadmap table.

## 5. Security Findings

| Finding | Severity | Location | Recommendation |
|---|---|---|---|
| “Safe” commands can execute blocked/destructive behavior without confirmation. Static validation accepted `awk 'BEGIN { system("rm -rf /tmp/x") }'` as `SAFE` and accepted `find /tmp -exec r"m" -rf {} \;` as `SAFE`; both are subsequently passed to the shell. | Critical | `src/invoq/core/tiers.py:13-30`, `src/invoq/core/parser.py:19-87`, `src/invoq/core/blocked_patterns.py:108-123`, `src/invoq/core/executor.py:331-337` | Replace base-command/regex classification with a fail-closed execution design: do not shell-execute commands classified only by executable name; parse a constrained AST or use structured, purpose-specific tools. Remove interpreter/exec-capable programs from `SAFE`, and regression-test obfuscation, `find -exec`, `awk system`, and shell expansions. |
| Direct writes are marked `SAFE`: `echo payload > /tmp/file`, `find /tmp -delete`, and `sed -i 's/a/b/' file` all validate as `SAFE`, so the user is not prompted. | Critical | `src/invoq/core/tiers.py:13-30`, `src/invoq/core/parser.py:75-84`, `src/invoq/core/validator.py:112-148` | Treat redirects and side-effecting options as confirmation-required or disallow them in safe mode. Split read-only tools from mutation tools with explicit parameters and confirmation. |
| The tool registry is an unrestricted execution bypass for extensions. `InvoqMCPServer` only specially protects two names and sends every other registered tool straight to its handler; `ToolRegistry.register` accepts any handler. An extension can register a tool that calls a subprocess without the validator or confirmation. | Critical | `src/invoq/mcp/server.py:50-55`, `src/invoq/mcp/registry.py:24-45,56-84` | Make the server, not a tool author, own the policy gate. Introduce a typed extension manifest with declared operations/commands, validator-mediated execution capabilities only, and deny arbitrary executable handlers. |
| `execute_script` performs line-oriented validation but executes the complete script with Bash. Shell grammar, multiline constructs, and expansions are not modelled; validation is therefore not equivalent to what runs. | High | `src/invoq/core/executor.py:180-259,359-382` | Do not accept arbitrary Bash scripts, or parse and execute an approved structured command list. If scripts remain, reject control syntax, substitutions, functions, and `-exec`/embedded-language constructs unless specifically supported. |
| The documented configuration controls (`require_confirmation`, `show_command_explanation`, and `allow_sudo_bypass`) are loaded but not consulted by execution. This creates misleading security/configuration semantics. | Medium | `src/invoq/config.py:20-25,73-82`, `src/invoq/core/executor.py:89-178` | Either implement each setting with secure defaults or remove it from defaults/UI/documentation. Do not add a sudo-bypass capability. |
| Input schemas define tool length and line limits, but registry dispatch invokes handlers with raw arguments and never instantiates the Pydantic models. For example, the `ExecuteCommandInput` maximum is unenforced. | Medium | `src/invoq/mcp/schemas.py:10-55`, `src/invoq/mcp/registry.py:56-84` | Bind a validated input schema to each registration and validate before invoking a handler; set resource limits at the execution boundary. |
| The blocked-pattern suite contains the required canonical cases, but only a small subset is tested and quote stripping permits pattern evasion. | High | `src/invoq/core/blocked_patterns.py:13-105`, `tests/test_validator.py:66-105` | Preserve canonical blocks as defense in depth, but test every required pattern plus whitespace, quoting, escaping, substitutions, and contextual bypasses. Do not treat regex matching as the primary security control. |

Static, non-executing validator checks confirmed that the canonical cases for `rm -r`, `rm -f`, `dd`, `mkfs.*`, `chmod 777`, direct `/dev/sd*` redirection, the tested fork-bomb form, and `shred` are blocked. That positive result does not mitigate the bypasses above.

## 6. MCP & Extension Architecture Review

For the built-in command tools, the normal path is LLM response → `InvoqMCPServer.handle_tool_call` → server validation → confirmation handler → `SafeExecutor.execute(..., skip_confirmation=True)` → executor revalidation → shell. This gives two validator calls and a confirmation request for commands classified as `CONFIRM`; `read_file`, `list_directory`, and `get_system_info` do not execute shell commands. The LLM is supplied the registry's tool list rather than a raw shell interface.

That boundary is only nominally contained. The final executor invokes a shell, while the validator recognizes only the first token of a simple segment and does not understand option semantics or embedded language. More importantly, the server dispatches every registered name other than `execute_command` and `execute_script` without any policy check. There is no implemented extension loader, isolation mechanism, manifest, command declaration workflow, or restriction preventing an extension handler from bypassing the validator. Consequently, the stated MCP containment and extension guarantees are not met.

## 7. Master Rules Violations

- **Files deleted instead of moved to `deprecated/`:** Git history records deletion of `temporary.txt` in `8653b59`; no `deprecated/` directory exists. This is low impact because the file was empty, but it conflicts with the stated rule if it applied to all tracked files.
- **Version source:** No duplicate static version definitions were found. Packaging uses `pyproject.toml`; the package fallback is only for an uninstalled checkout.
- **Emojis/style:** No non-ASCII characters were found in source, tests, scripts, configuration, or `pyproject.toml`. Comments are generally explanatory and not excessive.
- **Direct destructive operations:** Project lifecycle commands intentionally invoke package uninstallation and the uninstall script removes the application's own config/data. These are explicit user-facing lifecycle operations; they are separate from the LLM command path and are not classified as an audit violation.

## 8. Test Coverage Gaps

The suite covers parser basics, canonical validator cases, basic executor outcomes, command history, registry behavior, and filesystem tool happy paths. It does not cover:

- Validator bypasses, all blocked patterns, quoted/escaped/expanded inputs, side-effecting options, redirects, `find -exec`, embedded language, or Bash control structures.
- MCP server command/script confirmation approval, denial, edited-command revalidation, server/executor validator consistency, tool-call parsing edge cases, and `MCPClient` loops.
- Extension declaration, isolation, loading, or attempts to register an executable bypass tool.
- Configuration load/save/error handling, configuration flags, system detection, model recommendation/fit logic, Ollama client/manager error paths, setup workflow, prompts, Rich UI, install/update/uninstall scripts, or main CLI commands.
- Pydantic schemas and enforcement of command/script/file input limits.

Tests were not run: this checkout's environment lacks `rich`, and running the suite would create temporary/history files. `pytest` is also not declared in a development dependency group. The listed gaps are from static test inspection.

## 9. Specification Drift

The source specification is unavailable, so formal specification drift cannot be determined. Observable drift from the repository's public README and code promises includes:

- README documents `invoq debug` as debugging the last failed command, but `main.debug` only prints the version; `build_debug_prompt` is unused.
- README and installation guide say setup/installer installs Ollama. `run_setup` displays install instructions and asks the user to install it; it does not install Ollama.
- README advertises an `--execute` option whose description says commands execute automatically, but `run_ask` ignores this argument and executes every parsed tool call in both modes.
- The README labels the project a Linux assistant, yet `get_system_info` and prompt context include generic platform data. This is not cross-platform support by itself; the rest of the implementation and docs remain Linux-oriented.
- Extension configuration defaults to `git`, while the CLI only prints an extensions heading and no extension system is implemented.

## 10. Recommended Next Steps

1. Stop exposing the current shell and script execution tools to the LLM until the Critical bypasses are removed.
2. Redesign execution around explicit, structured operations or a strict, fail-closed command AST; classify redirects, in-place options, embedded code, and command-spawning options as non-safe by default.
3. Move validation and confirmation ownership into the server/execution capability itself. Make extensions declarative and unable to obtain raw subprocess access; add a security review gate before extension support is released.
4. Add adversarial regression tests for every reported bypass and each documented blocked class; test the complete MCP server → confirmation → executor path, not only the validator.
5. Restore the three source documents (including the version roadmap) to `docs/` and rerun this audit against them.
6. Decide whether to implement or remove the unused execution settings, `--execute` behavior, debug workflow, extension configuration, and schemas; then update README and installation documentation to match.
7. Add a development/test dependency group and run the suite in an isolated test environment after the security redesign.
