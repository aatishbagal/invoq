# Changelog

All notable changes to invoq are documented in this file.

The project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html) once
public releases begin.

## [Unreleased]

### Security

- Security coverage (R.6): add canonical blocked-pattern and audit-bypass
  matrices, including quoted, escaped, whitespace, and expansion variants.
  Exercise LLM payload parsing through the real server, confirmation handler,
  and executor with OS process creation mocked, including approval, denial,
  edited-command revalidation, and undeclared extension rejection.
- Group the existing R.0-R.5 regressions under `pytest -m security`, declare a
  `test` dependency extra, and run security and full suites in CI. Production
  execution policy is unchanged. See [security testing](docs/security-testing.md).
- Security fix (R.5): remove the unused execution configuration schema and all
  three settings from both default configs. Reject legacy execution sections
  with explicit migration guidance instead of silently ignoring their values.
  Confirmation and explanation behavior remains unchanged; no privilege-bypass
  capability is implemented. See [configuration migration](docs/configuration.md).
- Added regressions for removed configuration fields, default files, saved
  configuration, and rejection of legacy execution settings.
- Security fix (R.4): every registered tool now receives a strict Pydantic input
  schema enforced before dispatch. Command/script length limits and file line
  limits apply to built-ins, renamed tools, and commands edited at confirmation.
  Invalid types and extra fields fail closed before handlers run.
- Tool JSON schemas now advertise the same constraints and defaults enforced by
  the registry. Added regression coverage for oversized input, line bounds,
  malformed arguments, aliases, defaults, and edited-command length bypasses.
- Security fix (R.3, Option A): restrict `execute_script` to single-line literal
  commands joined only by `&&`. Independently validate every command before
  execution; reject control syntax, expansions, comments, shebangs, multiline
  input, and other separators. Execute the validated chain without a temporary
  Bash file. Existing confirmation and blocked-pattern checks remain enforced.
- Added executor regressions for rejected constructs, extension-enabled control
  words, independent validation, quoted literal syntax, and stop-on-failure
  behavior. See the [script contract](docs/security-classification.md).
- Security fix (R.2): every registered tool now requires an immutable capability
  declaration. Subprocess tools must provide a typed binding to the server's
  validator and confirmation path; direct registry execution is refused.
- Arbitrary Python handlers and callable validator hooks are rejected. Read-only
  registrations select reviewed built-in operations. This intentionally changes
  the registration API until an isolated extension runtime exists.
- Shell convenience functions now use the server gate. Complete scripts and
  edited commands are validated by the server; ambiguous confirmations and
  mismatched validator instances fail closed.
- Documented remaining read-only filesystem containment and disclosure gaps in
  the [tool capability policy](docs/security-tool-capabilities.md).
- Security fix (R.1): rebuilt command classification to fail closed on shell
  expansions, malformed syntax, assignments, and unsupported constructs. All
  pipeline, newline, and background segments are inspected; redirections
  require confirmation, including redirect-only commands.
- Removed interpreter, pager, helper-execution, and mutation-capable programs
  from SAFE. Decoded arguments now block embedded programs, interpreter execution
  options, `find` execution/deletion actions, in-place editing, and command wrappers.
- Validate complete scripts before execution and reject unsupported shebangs.
  Canonical destructive-operation blocks and the R.0 remediation gate remain
  enforced. See [classification policy](docs/security-classification.md) for
  the intentionally restricted syntax and command audit.
- Public release is blocked pending remediation of command-validation and MCP
  execution-boundary findings documented in the codebase audit.
- Added default-on `security.remediation_mode` to require manual approval for
  every allowed MCP `execute_command` and `execute_script` call, including SAFE
  classifications, with a startup warning. Blocked commands remain blocked.
- Added regression coverage for the blanket confirmation gate and audit
  bypass examples without executing their payloads. Classification is unchanged.

### Documentation

- Added project specification, development roadmap, and literature review.
- Added public-project guidance for contributing, security reporting, and
  releases.
- Updated the product roadmap to target Linux, macOS, and Windows in parallel.

## [0.12.1] - Unreleased

### Added

- Expanded CLI help and version flag variants.

### Changed

- Updated the README.

> Repository versions are not published releases. The current version is
> defined in `pyproject.toml`.
