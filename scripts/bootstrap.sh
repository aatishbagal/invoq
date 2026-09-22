#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "$(uname -s)" in
    Linux|Darwin) ;;
    *) echo 'Use scripts/install.ps1 or scripts/update.ps1 in Windows PowerShell.' >&2; exit 1 ;;
esac

for candidate in python3 python3.14 python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1 &&
        "$candidate" -I -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
        exec "$candidate" -I "$SCRIPT_DIR/../src/invoq/lifecycle.py" "$@"
    fi
done

echo 'Python 3.11+ is required. Install it, then rerun this script.' >&2
exit 1
