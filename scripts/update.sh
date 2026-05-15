#!/usr/bin/env bash
#
# invoq updater
# Usage: invoq self-update
#        or: curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/invoq/main/scripts/update.sh | bash
#

set -euo pipefail

echo "Updating invoq..."

if command -v pipx &>/dev/null && pipx list 2>/dev/null | grep -q invoq; then
    pipx upgrade invoq
elif command -v pip3 &>/dev/null; then
    pip3 install --user --upgrade invoq
elif command -v pip &>/dev/null; then
    pip install --user --upgrade invoq
else
    echo "Error: Could not find pip or pipx."
    exit 1
fi

echo ""
echo "Done. Current version:"
invoq --version
