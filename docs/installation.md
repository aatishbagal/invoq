# Installation Guide

> Unstable beta: installers support Linux, macOS, and Windows. Command execution
> remains Linux-first; native macOS and Windows execution adapters are still
> development work. See [release requirements](../RELEASING.md).

## Release status

The beta installs the current `main` commit from this repository, pinned to its
full Git commit ID. Stable installation requires a published GitHub release
and a matching wheel with a SHA-256 digest. Both channels install directly from
this repository's GitHub sources and release artifacts.

## Install the beta

Install Python 3.11+ and Git. On Linux, ensure Python's `venv` and `ensurepip`
support is installed (Debian/Ubuntu package it as `python3-venv`). On macOS, use
a current Python installation rather than the older system Python. On Windows,
install Python with the `py` launcher or add Python to PATH.

**Linux / macOS:**

```bash
curl -fsSL https://raw.githubusercontent.com/aatishbagal/invoq/main/scripts/install.sh | bash
```

**Windows PowerShell:**

```powershell
irm https://raw.githubusercontent.com/aatishbagal/invoq/main/scripts/install.ps1 | iex
```

No repository checkout is needed. The script fetches the shared installer from
`main`, then resolves and installs the latest `main` commit. The downloaded
helper is retained in the system temporary directory. From an existing source
checkout, `bash scripts/install.sh` and `.\scripts\install.ps1` also work.

The installer uses a private environment, selects its own Python for pip, and
records the channel and installed source in `invoq-install.json` within that
environment. Existing directories without a valid installer receipt are
refused. No system packages, shell profiles, or user configuration are changed.

| Platform | Beta environment | Executable directory |
| --- | --- | --- |
| Linux / WSL | `~/.local/share/invoq/beta` | `bin` |
| macOS | `~/Library/Application Support/invoq/beta` | `bin` |
| Windows | `%LOCALAPPDATA%\invoq\beta` | `Scripts` |

Run the PATH command printed by the installer. It applies to the current
terminal. To keep it for future terminals, add that same directory to your
shell profile or Windows user PATH. Verify with `invoq --version`, then run
`invoq setup`. The installer does not start setup or download models itself.

## Update and recover

Run `invoq self-update` to get the newest source on the installed channel.
The installed receipt keeps beta users on beta and stable users on stable.
The updater verifies installed package provenance, resolves a pinned source,
reinstalls into the same environment, and records success only after verifying
the installed source. If the source is unchanged, no packages are reinstalled.

On Windows, updating from `invoq.exe` opens a separate window, waits for the
launcher to exit, and shows the result there. Press Enter to close that window
after reading the result. The checkout update scripts run synchronously.

From a checkout, `bash scripts/update.sh` or `.\scripts\update.ps1` updates the
beta synchronously using the managed environment's Python. For stable, pass
`stable` to the Bash script or `-Channel stable` to the PowerShell script.
Keep Git installed for beta updates. The checkout is only needed for these
wrapper scripts or recovery; ordinary self-update fetches updates itself.

If an install/update is interrupted, rerun the installer for the same channel.
Package installation is not transactional: a failed pip operation can leave an
incomplete environment. The installer can repair its existing environment;
it does not clear directories or reset user settings. Older or editable
installs lack the receipt and receive migration guidance. Run the new installer
and use its printed PATH to select the new copy.

## Stable releases

Once a stable release is available, use:

```bash
curl -fsSL https://raw.githubusercontent.com/aatishbagal/invoq/main/scripts/install.sh | bash -s -- stable
```

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/aatishbagal/invoq/main/scripts/install.ps1))) -Channel stable
```

Stable uses a separate `stable` environment at the
same platform-specific location. It requires the latest non-draft,
non-prerelease GitHub release, a semantic-version tag, and a universal wheel
whose filename matches that tag. The GitHub-provided SHA-256 digest is required
and pip checks it during download. Missing releases, wheels, checksums, or
network access fail without switching channels or selecting another source.

## Linux development prerequisites

### Prerequisites

**Fedora/RHEL:**
```bash
sudo dnf install python3.11 python3-pip
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3-pip
```

**Arch:**
```bash
sudo pacman -S python python-pip
```

For source-checkout setup, tests, and contribution guidance, see
[`../CONTRIBUTING.md`](../CONTRIBUTING.md). The commands below are operating
system prerequisites for Linux development; they are not a release installer.

### Ollama and first-time setup

Install Ollama yourself before running `invoq setup`; invoq does not install
Ollama. Follow the installation instructions for your operating system from
[Ollama](https://ollama.com/download).

From your configured source-checkout environment, run:

```bash
invoq setup
```

The wizard checks hardware and Ollama availability. If Ollama is missing, it
prints installation instructions and asks you to install it yourself before
rechecking. It can offer to start an existing installation, recommends or accepts
a model, downloads the model if needed, verifies it, and saves the configuration.

## Linux GPU development notes

| GPU | Support | Notes |
|-----|---------|-------|
| NVIDIA | Full | CUDA acceleration, fastest |
| AMD | Partial | ROCm required, good performance |
| Intel Arc | Experimental | Works but not optimized |
| Integrated | CPU fallback | Uses CPU instead (slower but works) |

## Linux development troubleshooting

### Ollama not starting

Try starting Ollama manually:

```bash
ollama serve
```

If it fails, check the Ollama logs and the installation instructions for your
operating system at [Ollama](https://ollama.com/download).

### Model download fails during development

Download the model manually:

```bash
ollama pull qwen2.5-coder:7b
```

Then re-run `invoq setup`.
