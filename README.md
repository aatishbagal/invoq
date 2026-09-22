# invoq

Cross-platform AI Terminal Assistant — natural language to terminal operations,
powered by local LLMs.

## Project status

invoq is pre-release software targeting Linux, macOS, and Windows.
Command-execution security and platform adapters are being hardened before a
public release. The current implementation is Linux-first; macOS and Windows
are not supported releases yet. Do not use it for privileged, production, or
irreversible work.

MCP command execution runs in remediation mode by default. The
`security.remediation_mode` setting forces manual approval for every allowed
`execute_command` and `execute_script` call, including commands classified as
SAFE. Blocked commands remain blocked. Startup logs:
`Running in remediation mode: all command execution requires manual approval.`
Keep this setting enabled until the command-classification remediation is
complete. This temporary gate does not change command classification.

Command classification now rejects unsupported shell syntax and known execution
or mutation bypasses. Redirects require confirmation. The supported syntax and
command audit are documented in [Classification policy](docs/security-classification.md).

Every registered execution tool now passes through the server's validator and
confirmation handler. Arbitrary Python tool handlers are refused. Registration
examples and the read-only tool audit are in [Tool capability policy](docs/security-tool-capabilities.md).

> The PyPI distribution name `invoq` currently belongs to an unrelated
> project. Do not use `pip install invoq` or this repository's current
> installer until the project publishes under its own verified distribution
> name.

## Installation

There is no public installation command yet. A release will publish a unique,
verified distribution name and immutable installation instructions after the
security and release gates in [RELEASING.md](RELEASING.md) are complete.

For contributor setup from a source checkout, see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Platform targets

| Platform | Status |
|----------|--------|
| Linux | Current implementation base; not released |
| macOS | Active development target; not released |
| Windows | Active development target through PowerShell; not released |

## Requirements

- Linux, macOS, or Windows for the future supported product
- Python 3.11+
- 4GB+ RAM (8GB recommended)
- ~5GB disk space for AI models

## Current CLI

The implemented workflows are available from a source checkout:

```bash
invoq ask "find all large files over 100MB"    # Natural language to command
invoq explain "tar -xzvf archive.tar.gz"       # Explain a command
invoq setup                                     # Run setup wizard
```

`ask` dispatches model tool calls through the MCP policy and confirmation gate.
It has no dry-run mode. The ignored `--execute` / `-e` flag has been removed;
use `invoq ask "your prompt"` without it. `explain` explains a supplied shell
command without executing it.

`invoq debug` is not yet implemented and reports that status with a nonzero
exit code. Use `invoq --version` to display the installed version.

Extensions are not yet implemented. `invoq extensions list` reports that status
with a nonzero exit code. No extensions are loaded, and none are enabled by
default; the extension framework is deferred to Phase 6.

## Configuration

Configuration lives at `~/.config/invoq/config.yaml`. The unused `execution`
section has been removed. Existing configs containing it are rejected with
migration instructions; remove that section before restarting invoq.
Confirmation and explanation display have no configuration toggles. The MCP
remediation gate remains enabled by default, and CONFIRM-tier commands still
require approval when remediation mode is disabled. There is no sudo-bypass
feature. See [Configuration](docs/configuration.md) for defaults and migration.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report
security vulnerabilities privately as described in [SECURITY.md](SECURITY.md).
Release gates and the publishing procedure are in [RELEASING.md](RELEASING.md).

## License

Copyright © 2026 Aatish Bagal. Licensed under the [MIT License](LICENSE).
