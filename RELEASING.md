# Releasing invoq

This document defines the minimum release gate for the Linux, macOS, and
Windows CLI. A version in `pyproject.toml` is not a public release by itself.

## Release blockers

Do not publish while any critical command-execution, validation, confirmation,
MCP-boundary, or extension-isolation finding remains open. Resolve the
findings in the audit and add regression tests before creating the first
release.

Distribute invoq through this repository's GitHub installers and release
artifacts. Package-index publication is not part of the current release plan.

## Required release infrastructure

Before the first release, add and verify:

- Native Linux, macOS, and Windows CI that installs the package in a clean
  environment and runs the test suite on every pull request and release tag.
- A release workflow that builds an sdist and wheel from an immutable tag.
- A protected workflow that uploads release artifacts to GitHub Releases.
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

The paste-and-run bootstrap is served from `main`. It downloads the shared
installer from the same branch. Stable installation uses a checksummed release
wheel, and beta installation records a full commit ID. Update and uninstall
flows must target the same installation and clearly state their effects.

The unstable-beta installer resolves this repository's `main` branch to a full
commit ID and installs that revision in a private environment. Beta updates
remain on `main`. This channel is experimental and does not waive the stable
release gates above.

The stable installer and updater read this repository's latest non-draft,
non-prerelease GitHub release. Publish a tag of the form `vMAJOR.MINOR.PATCH`
and upload `invoq-MAJOR.MINOR.PATCH-py3-none-any.whl` with the same version as
`pyproject.toml`. The release asset must expose a GitHub SHA-256 digest; the
installer requires it and pip validates the downloaded wheel against it.
Without that artifact, stable installation fails closed.

Beta and stable environments have separate installation receipts, and
`invoq self-update` preserves the installed channel. The installation CI checks
platform-specific paths, entry points, failure handling, and pinned-source
selection; native end-to-end release installation is still a release gate.
