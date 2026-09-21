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

## Intended CLI

The following is the intended cross-platform CLI surface. Some commands remain
incomplete while the project is pre-release; see the audit and changelog for
current status.

```bash
invoq ask "find all large files over 100MB"    # Natural language to command
invoq debug                                     # Debug last failed command
invoq explain "tar -xzvf archive.tar.gz"       # Explain a command
invoq setup                                     # Run setup wizard
invoq self-update                               # Update to latest version
```

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report
security vulnerabilities privately as described in [SECURITY.md](SECURITY.md).
Release gates and the publishing procedure are in [RELEASING.md](RELEASING.md).

## License

Copyright © 2026 Aatish Bagal. Licensed under the [MIT License](LICENSE).
