# Installation Guide

## One-Line Install (Recommended)

The fastest way to get started:

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/invoq/main/scripts/install.sh | bash
```

## What the Installer Does

1. **Checks Python version** - Requires Python 3.11+
2. **Installs invoq** - Uses pipx if available, otherwise pip --user
3. **Updates PATH** - Adds ~/.local/bin to your PATH if needed
4. **Runs setup wizard** - Detects hardware, installs Ollama, downloads AI model

## Manual Installation

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

### Install with pipx (Recommended)

pipx installs Python applications in isolated environments:

```bash
# Install pipx if you don't have it
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install invoq
pipx install invoq
```

### Install with pip

```bash
pip install --user invoq
```

### Run Setup

After installation, run the setup wizard:

```bash
invoq setup
```

This will:
- Detect your system specs (RAM, GPU)
- Install Ollama if not present
- Download an appropriate AI model
- Verify everything works

## GPU Support

| GPU | Support | Notes |
|-----|---------|-------|
| NVIDIA | Full | CUDA acceleration, fastest |
| AMD | Partial | ROCm required, good performance |
| Intel Arc | Experimental | Works but not optimized |
| Integrated | CPU fallback | Uses CPU instead (slower but works) |

## Troubleshooting

### "invoq: command not found"

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

### Model download fails

Download the model manually:

```bash
ollama pull qwen2.5-coder:7b
```

Then re-run `invoq setup`.
