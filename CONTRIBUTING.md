# Contributing to invoq

Thank you for helping improve invoq. The project is a cross-platform CLI that
uses a local LLM to help users work in the terminal. Linux is the current
implementation base; macOS and Windows are active development targets. It is
pre-release and not yet ready for general command execution.

## Scope

- Target Linux, macOS, and Windows as equal first-release platforms. Windows
  support is based on PowerShell; `cmd.exe` requires a separate future design.
- Keep platform-specific behavior behind a capability contract and native
  adapter. Do not turn one platform's command into another's by string
  replacement.
- Keep model interaction local through Ollama; do not add cloud model support
  without an explicit design decision.
- Treat command validation, confirmation, MCP containment, and extension
  isolation as security-critical code.
- Do not introduce a path that gives an LLM raw subprocess access or lets a
  tool bypass validation and confirmation.

## Before opening an issue

- Search existing issues and the roadmap in
  [`docs/development-prompts.md`](docs/development-prompts.md).
- Report a reproducible bug with the operating system and version, shell or
  PowerShell version, Python version, invoq revision, expected result, and
  actual result.
- Do not include credentials, private file contents, or security exploit
  details in public issues. Follow [SECURITY.md](SECURITY.md) for security
  reports.

## Development setup

invoq requires Python 3.11 or newer. Until test dependencies are declared in
`pyproject.toml`, install them explicitly in an isolated virtual environment.
Use the native terminal for the platform being tested. The following is the
current POSIX-shell example:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e . pytest pytest-asyncio
.venv/bin/python -m pytest
```

Do not run tests that execute commands against a personal or production
machine. Use mocks, temporary directories, or an isolated test host for the
target platform.

## Pull requests

1. Start from the current default branch and keep each change focused.
2. Add or update tests for changed behavior on Linux, macOS, and Windows.
   Security changes require regression tests for the bypass or unsafe input on
   every applicable platform.
3. Update user-facing documentation and `CHANGELOG.md` when applicable.
4. Run the relevant tests and state exactly what you ran in the pull request.
5. Do not include generated build artifacts, virtual environments, secrets, or
   unrelated formatting changes.

## Code and security expectations

- Prefer explicit, readable code and keep comments purposeful.
- Preserve the fail-closed model: unknown operations must not execute.
- Require a user confirmation for every operation that may change state.
- Never weaken a block, validator, confirmation step, or extension boundary
  merely to support a feature. Propose the threat model and tests first.

By contributing, you agree that your contributions may be distributed under
the [MIT License](LICENSE).
