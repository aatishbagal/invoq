# Installation Guide

> This is the current Linux development-installation guide, not a public
> release guide. Linux, macOS, and Windows are equal release targets, but
> macOS and Windows installers are not available yet. Do not use
> `pip install invoq`: that PyPI name belongs to an unrelated project. See
> [`../RELEASING.md`](../RELEASING.md) for release requirements.

## Release status

No public installer or package is available yet. A release will provide
verified, immutable installation instructions for Linux, macOS, and Windows
after the security and release gates are complete.

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

## Linux GPU development notes

| GPU | Support | Notes |
|-----|---------|-------|
| NVIDIA | Full | CUDA acceleration, fastest |
| AMD | Partial | ROCm required, good performance |
| Intel Arc | Experimental | Works but not optimized |
| Integrated | CPU fallback | Uses CPU instead (slower but works) |

## Linux development troubleshooting

### Shell path setup

Your PATH doesn't include the install location. Add this to your ~/.bashrc or ~/.zshrc:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then restart your terminal or run `source ~/.bashrc`.

### Ollama not starting

Try starting Ollama manually:

```bash
ollama serve
```

If it fails, check the Ollama logs or reinstall:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Model download fails during development

Download the model manually:

```bash
ollama pull qwen2.5-coder:7b
```

Then re-run `invoq setup`.
