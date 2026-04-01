#!/usr/bin/env bash
#
# invoq uninstaller
# Usage: curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/invoq/main/scripts/uninstall.sh | bash
#        or: invoq self-uninstall
#

set -euo pipefail

# -- colors --

if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# -- confirmation --

echo "This will remove invoq from your system."
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# -- remove invoq --

info "Removing invoq..."

if command -v pipx &>/dev/null && pipx list 2>/dev/null | grep -q invoq; then
    pipx uninstall invoq
    success "Removed via pipx"
elif command -v pip3 &>/dev/null; then
    pip3 uninstall invoq -y 2>/dev/null && success "Removed via pip3" || warn "pip3 uninstall failed (may not have been installed with pip)"
elif command -v pip &>/dev/null; then
    pip uninstall invoq -y 2>/dev/null && success "Removed via pip" || warn "pip uninstall failed"
else
    warn "Could not find pip or pipx to uninstall invoq."
fi

# -- optionally remove config --

echo ""
read -p "Remove config files (~/.config/invoq)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$HOME/.config/invoq"
    success "Config removed"
fi

# -- optionally remove history --

read -p "Remove command history (~/.local/share/invoq)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$HOME/.local/share/invoq"
    success "History removed"
fi

# -- PATH note --

echo ""
warn "Note: The PATH entry added by invoq installer was not removed."
echo "You can manually remove the '# Added by invoq installer' lines from your shell rc file if desired."
echo ""
success "invoq has been uninstalled."
