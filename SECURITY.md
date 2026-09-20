# Security Policy

## Project status

invoq is pre-release software targeting Linux, macOS, and Windows. It can
generate and execute terminal operations, so its platform adapters,
command-validation, confirmation, MCP tool boundary, and extension model are
security-critical. Do not rely on any unreleased revision for production,
privileged, or irreversible workloads.

There are currently no supported public releases. The project will publish a
supported-version table here when its first release is available.

## Reporting a vulnerability

Please do not disclose vulnerabilities in a public issue, discussion, pull
request, or commit message.

Use GitHub's private vulnerability-reporting feature for this repository when
it is available. If it is unavailable, contact the repository owner privately
through their GitHub profile and include only a request for a secure reporting
channel in public communication.

Include:

- A clear description of the issue and its impact.
- The affected revision or commit.
- Reproduction steps or a minimal proof of concept.
- Whether user confirmation, the validator, a blocked pattern, MCP routing, or
  an extension boundary can be bypassed, including the affected platform and
  shell.
- Suggested mitigations, if known.

Do not run destructive proof-of-concept commands on a real system. Prefer an
isolated VM/container and a harmless substitute target.

## Security priorities

Reports involving any of the following are treated as high priority:

- An LLM executing a command that bypasses validation or user confirmation.
- Evasion of a blocked command or argument restriction on Bash, Zsh, or
  PowerShell.
- A registered MCP tool or extension obtaining unmediated subprocess access.
- Unintended access to files, credentials, or local services.
- Supply-chain issues in installation, update, packaging, or release flows.

## Disclosure process

The maintainer will acknowledge a valid report, assess impact, develop and
test a fix, and coordinate disclosure with the reporter where possible. Do
not publish details until a fix or mitigation is available and a disclosure
timeline has been agreed.

Security fixes will be documented in [CHANGELOG.md](CHANGELOG.md) without
including exploit instructions.
