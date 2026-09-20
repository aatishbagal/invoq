# Changelog

All notable changes to invoq are documented in this file.

The project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html) once
public releases begin.

## [Unreleased]

### Security

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
