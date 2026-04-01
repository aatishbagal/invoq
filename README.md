# invoq

Linux AI Terminal Assistant - Natural language to shell commands, powered by local LLMs.

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/invoq/main/scripts/install.sh | bash
```

This will:
1. Install invoq via pipx (or pip)
2. Add it to your PATH
3. Launch the interactive setup wizard

## Manual Install

```bash
# Using pipx (recommended)
pipx install invoq

# Or using pip
pip install --user invoq

# Then run setup
invoq setup
```

## Requirements

- Linux (tested on Fedora, Ubuntu, Arch)
- Python 3.11+
- 4GB+ RAM (8GB recommended)
- ~5GB disk space for AI models

## Commands

```bash
invoq ask "find all large files over 100MB"    # Natural language to command
invoq debug                                     # Debug last failed command
invoq explain "tar -xzvf archive.tar.gz"       # Explain a command
invoq setup                                     # Run setup wizard
invoq self-update                               # Update to latest version
```

## Uninstall

```bash
invoq self-uninstall
```

Or manually:
```bash
pipx uninstall invoq  # or: pip uninstall invoq
rm -rf ~/.config/invoq ~/.local/share/invoq
```
