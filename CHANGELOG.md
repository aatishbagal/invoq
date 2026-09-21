# Changelog

All notable changes to invoq are documented in this file.

The project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html) once
public releases begin.

## [Unreleased]

### Security

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
