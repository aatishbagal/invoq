# invoq - Project Specification

> Cross-Platform AI Terminal Orchestrator
> Planning Version: 2.0
> Last Updated: September 2026

---

## Quick Reference

### Core Features
1. Local AI Models (Ollama/llama.cpp)
2. Natural Language to Command
3. Temporary Script Generation
4. Debug Last Command
5. Explain Commands
6. Command History

### Security Features
7. Allowlist-Based Execution
8. Blocked Dangerous Commands
9. Mandatory User Confirmation
10. Sudo Warnings

### Extension System
11. Modular Extensions
12. Git Extension (built-in)
13. Python Extension (optional)
14. GCC Extension (optional)
15. Docker Extension (optional)

### User Experience
16. CLI Only
17. 4GB RAM Support
18. Auto Model Selection
19. Streaming Output
20. Cross-platform package distribution and release artifacts

---

## Technology Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.11+ |
| CLI Framework | Typer |
| Terminal UI | Rich |
| Async | asyncio + anyio |
| Config | PyYAML |
| LLM Backend | Ollama (primary), llama-cpp-python (alt) |
| Protocol | MCP (Model Context Protocol) |
| Testing | pytest + pytest-asyncio |

## Platform Support

Linux, macOS, and Windows are equal targets for the first public release.
Current source code is Linux-first and does not yet provide released macOS or
Windows support. Platform support is complete only when the platform has a
native execution adapter, confirmation flow, data/config paths, installer and
uninstaller, and integration coverage.

| Platform | Target shell | Current status | 1.0 requirement |
|----------|--------------|----------------|-----------------|
| Linux | POSIX shell | Implementation base | Supported |
| macOS | Zsh/POSIX shell adapter | Planned | Supported |
| Windows | PowerShell adapter | Planned | Supported |

`cmd.exe` is not part of the initial Windows target. It requires a separate
adapter and policy before it can be supported.

---

## Model Recommendations

| RAM | Model | Notes |
|-----|-------|-------|
| 4GB | Qwen2.5-Coder 1.5B or Phi-3 Mini | Proven for shell/code tasks |
| 6-8GB | Qwen2.5-Coder 7B (Q4) | Excellent, competitive with GPT-4o |
| 8GB+ | Qwen2.5-Coder 7B | Full capability |

**Internet Access**: NOT required for core functionality. Models know shell commands, scripting, and common error patterns from training data.

---

## Security Model

### Command Tiers

| Tier | Behavior | Examples |
|------|----------|----------|
| Safe | Read-only structured operation; no shell escape, redirect, or embedded program | platform-specific inspection operations |
| Confirm | State-changing operation requiring explicit approval | platform-specific file, package, and project operations |
| Blocked | NEVER allowed via AI | destructive or policy-bypassing operations |

### Platform-Aware Blocked Operations (Never Allowed)

- Recursive/forced deletion and destructive disk or filesystem operations.
- Unsafe permission changes, direct block-device writes, fork bombs, and
  secure-wipe operations.
- Shell escapes, embedded interpreters, redirects, or command substitutions
  that bypass the structured policy.
- The equivalent native operation on Linux, macOS, or Windows.

Each platform adapter must define and test its own blocked operations. A
pattern written for Bash must not be assumed to protect PowerShell.

### Security Principle
**Structured allowlist over shell parsing**: Only explicitly permitted,
platform-native operations can execute. Unknown operations are blocked by
default, and any operation that may change state requires user confirmation.

---

## Development Phases

| Phase | Focus | Duration |
|-------|-------|----------|
| 1 | Project Foundation | Week 1 |
| 2 | Command Validation & Security | Week 1-2 |
| 3 | Core AI Features | Week 2-3 |
| 4 | CLI Integration | Week 3-4 |
| 5 | Extension System | Week 4-5 |
| 6 | Shell Integration | Week 5 |
| 7 | Polish & Packaging | Week 6 |
| 8 | Future Features | Post-release |

> **Note:** This phase table reflects the original v1.2 plan. See `development-prompts.md` for the current, more detailed phase breakdown (which restructures MCP server work into its own dedicated phase).

---

## Future Features (v2.0+)

### Internet Access (Planned)

Optional web search capability via MCP tool:
- Looking up current package/library versions
- Searching Stack Overflow for specific errors
- Checking documentation for newer tools
- Verifying command syntax for obscure utilities

Implementation approach:
- Add as optional MCP tool (disabled by default)
- Use privacy-focused search (SearXNG or similar)
- User must explicitly enable in config
- All searches logged for transparency

**Note**: Internet is NOT required for v1.0. Core functionality works completely offline.

---

## Out of Scope (v1.0)

- Graphical user interface
- Cloud/remote model support
- Multi-model conversations
- Voice input
- Dotfile modification features
- Semantic search over command history
- NPU/GPU acceleration
- Web interface
- Mobile companion app

---

## Success Criteria

| Criteria | Target |
|----------|--------|
| Command Generation | Works for common shell tasks |
| Security | Blocks all dangerous commands |
| Performance | <15s response on 4GB RAM |
| Platform support | Core workflows work on Linux, macOS, and Windows |
| Installation | Verified native installation works on each supported platform |
| Extensibility | New tools addable without core changes |
| Debugging | Identifies common errors accurately |

---

## CLI Commands

```
invoq <prompt>              # Generate command from natural language
invoq debug                 # Debug last failed command
invoq explain <cmd>         # Explain what a command does
invoq history               # Show recent commands
invoq config show           # Show configuration
invoq config set <k> <v>    # Set config value
invoq extensions list       # List extensions
invoq extensions enable     # Enable extension
invoq shell install         # Install shell hooks
```

---

## File Structure

```
src/invoq/
├── main.py              # CLI entry point
├── config.py            # Configuration
├── exceptions.py        # Custom exceptions
├── core/
│   ├── validator.py     # Command validation
│   ├── executor.py      # Safe execution
│   ├── history.py       # Command history
│   ├── generator.py     # NL to command
│   ├── debugger.py      # Debug feature
│   └── explainer.py     # Explain feature
├── llm/
│   ├── ollama.py        # Ollama client
│   └── model_selector.py
├── platforms/            # Native execution, paths, and shell adapters
│   ├── linux.py
│   ├── macos.py
│   └── windows.py
├── extensions/
│   ├── base.py          # Extension framework
│   └── git/             # Git extension
├── shell/
│   └── hooks.py         # Shell integration
└── ui/
    └── confirmation.py  # Confirmation UI
```

> **Note:** This is the original v1.2 file layout. The current build plan in `development-prompts.md` adds `mcp/`, `prompts/`, and `cli/` packages as part of the MCP-based architecture — refer to that document's file structure for the up-to-date layout.

---

*This specification is the source of truth for development.*
