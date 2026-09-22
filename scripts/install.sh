#!/usr/bin/env bash
set -euo pipefail

case "$(uname -s)" in
    Linux|Darwin) ;;
    *) echo 'Use the PowerShell installer on Windows.' >&2; exit 1 ;;
esac

PYTHON_CMD=''
for candidate in python3 python3.14 python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1 &&
        "$candidate" -I -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
        PYTHON_CMD="$candidate"
        break
    fi
done
if [[ -z "$PYTHON_CMD" ]]; then
    echo 'Python 3.11+ is required. Install it, then rerun the installer.' >&2
    exit 1
fi

INSTALLER=''
if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
    SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
    if [[ -f "$SCRIPT_DIR/../src/invoq/lifecycle.py" ]]; then
        INSTALLER="$SCRIPT_DIR/../src/invoq/lifecycle.py"
    fi
fi
if [[ -z "$INSTALLER" ]]; then
    INSTALLER="$(mktemp "${TMPDIR:-/tmp}/invoq-installer.XXXXXXXX")"
    curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
        --output "$INSTALLER" \
        https://raw.githubusercontent.com/aatishbagal/invoq/main/src/invoq/lifecycle.py
fi

exec "$PYTHON_CMD" -I "$INSTALLER" install "$@"
