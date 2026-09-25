# Security testing

Install from a source checkout in an isolated Python 3.11+ environment:

```bash
python -m pip install ".[test]"
python -m pytest -m security -q
python -m pytest -q
```

The `test` extra installs pytest, pytest-asyncio, and Rich alongside the project's
runtime dependencies. The `security` marker is registered with strict marker
checking. No test is removed or relocated: module markers collect the existing
R.0-R.5 tests alongside the consolidated adversarial suite.

## Coverage

| Area | Coverage |
| --- | --- |
| Canonical blocks | Recursive/forced deletion, root/home deletion, disk writes, filesystem formatting, world-writable permissions, block-device redirects, fork bombs, shredding, remote shell pipelines, privileged deletion, history clearing, critical system-file writes, and firewall disabling |
| Obfuscation | Canonical, quoted, escaped, and whitespace variants for every blocked-pattern category |
| Audit bypasses | `awk system`, `find -exec`, `find -delete`, `echo` redirects, and `sed -i`, each with executable escaping, command substitution, and environment-variable variants |
| macOS/BSD | Explicit `diskutil` and `newfs_*` blocks, raw/block disk-device redirects and operands, BSD sed/find/awk forms, and macOS prompt context; all cases run on every host |
| Full execution path | Native tool-call payloads and JSON content pass through `MCPClient`, server parsing, schema validation, `ConfirmationHandler`, and `SafeExecutor` |
| Confirmation | Command/script approval and denial, default remediation approval for SAFE commands, mandatory redirect confirmation with remediation disabled, and unavailable input |
| Edits | Allowed edits revalidated by confirmation, server, and executor; blocked edits and oversized edits never reach a process |
| Scripts | Approved flat chains validated command by command; unsupported scripts rejected even after approval |
| Extensions | Undeclared or falsely read-only Python process handlers refused before dispatch |
| Earlier remediations | Config migration, schemas, capability bindings, script restrictions, parser/classifier cases, and the remediation gate remain covered by their original tests |

Ordinary file redirects remain CONFIRM; obfuscated expansions and prohibited
operations remain BLOCKED. Tests assert these tiers explicitly.
The [macOS audit](macos-security-audit.md) records the BSD syntax review,
pre-fix failures, and the device-path policy's scope.

## Isolation

`tests/test_security_regressions.py` never runs its adversarial payloads. It
replaces asynchronous OS process creation and guards synchronous `Popen` calls.
The successful process results are simulated; the server, validator,
confirmation handler, and executor logic remain real. Console input and editor
results are simulated, and history writes are mocked.

The broader existing suite includes benign subprocess tests and temporary-file
tests. Run it in an isolated development environment or disposable CI runner;
it is not a sandbox for arbitrary payloads. The tests make no LLM network calls.

## CI

The [security workflow](../.github/workflows/security.yml) runs the marked and
full suites on Python 3.11 and 3.14. It uses read-only repository permissions,
does not retain checkout credentials, and pins the checkout and Python setup
actions to release commit SHAs. It runs on pushes to `dev`, pull requests to
`dev` or `main`, and manual dispatch.

This suite verifies the current restricted execution contract. It does not
establish a subprocess sandbox or prove unrestricted shell syntax safe.
