# Releasing invoq

This document defines the minimum release gate for the Linux, macOS, and
Windows CLI. A version in `pyproject.toml` is not a public release by itself.

## Release blockers

Do not publish while any critical command-execution, validation, confirmation,
MCP-boundary, or extension-isolation finding remains open. Resolve the
findings in the audit and add regression tests before creating the first
release.

The PyPI name `invoq` is already used by an unrelated project. Before any
package release, choose and reserve a unique distribution name. The console
command may remain `invoq`, but installation instructions must use the chosen
distribution name and must never direct users to the unrelated package.

## Required release infrastructure

Before the first release, add and verify:

- Native Linux, macOS, and Windows CI that installs the package in a clean
  environment and runs the test suite on every pull request and release tag.
- A release workflow that builds an sdist and wheel from an immutable tag.
- PyPI Trusted Publishing for the repository; do not upload long-lived API
  tokens from a workstation.
- Package metadata: license, project URLs, classifiers, README metadata, and
  declared development/test dependencies.
- A GitHub Release with release notes and checksums for published artifacts.

## Release procedure

1. Confirm the working tree is clean and the target branch is up to date.
2. Review open security reports and the audit; every release blocker must be
   resolved or explicitly removed from scope.
3. Run the full test suite on clean Linux, macOS, and Windows environments and
   validate a clean install of the built wheel on each platform.
4. Update `CHANGELOG.md` and the package version in the single authoritative
   source, `pyproject.toml`.
5. Create and push an annotated version tag, for example `v1.0.0`.
6. Let the protected release workflow build and publish the artifacts.
7. Verify the uploaded package metadata, files, checksums, entry point, and
   installation from independent clean Linux, macOS, and Windows environments.
8. Create the matching GitHub Release and update installation instructions to
   reference the immutable published version or release artifact.

## Installer requirements

The public installer must not fetch a mutable branch and execute it without a
version/checksum trail. It should install a pinned, verified release artifact
or a precisely versioned package. Update and uninstall flows must use the same
distribution name and clearly state their effects before changing a system.
