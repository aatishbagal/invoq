#!/usr/bin/env bash
#
# invoq installer
# Usage: curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/invoq/main/scripts/install.sh | bash
#
# This script:
# 1. Checks system requirements
# 2. Installs invoq via pipx (preferred) or pip
# 3. Adds invoq to PATH if needed
# 4. Runs invoq setup wizard
#

set -euo pipefail

# -- colors (disable if not tty) --

if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    BOLD=''
    NC=''
fi

# -- helpers --

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# -- error trap --

cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        echo ""
        echo -e "${RED}Installation failed.${NC}"
        echo "If this is a bug, please report it at:"
        echo "  https://github.com/YOUR_USERNAME/invoq/issues"
    fi
}
trap cleanup EXIT

# -- header --

echo -e "${BOLD}"
echo '  _                        '
echo ' (_)_ ____   _____   __ _ '
echo " | | '_ \\ \\ / / _ \\ / _' |"
echo ' | | | | \ V / (_) | (_| |'
echo ' |_|_| |_|\_/ \___/ \__, |'
echo '                      | | '
echo '                      |_| '
echo -e "${NC}"
echo 'Linux AI Terminal Assistant'
echo ''

# -- OS check --

detect_os() {
    local os
    os="$(uname -s)"
    case "$os" in
        Linux)
            if grep -qi microsoft /proc/version 2>/dev/null; then
                echo "wsl"
            else
                echo "linux"
            fi
            ;;
        Darwin)
            echo "macos"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

OS="$(detect_os)"

case "$OS" in
    linux|wsl)
        success "Detected Linux"
        ;;
    macos)
        warn "macOS detected. invoq is only tested on Linux."
        read -p "Continue anyway? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cancelled."
            exit 0
        fi
        ;;
    *)
        error "Unsupported operating system. invoq requires Linux."
        ;;
esac

# -- Python check --

detect_distro() {
    if [[ -f /etc/os-release ]]; then
        # shellcheck source=/dev/null
        . /etc/os-release
        echo "${ID:-unknown}"
    else
        echo "unknown"
    fi
}

check_python() {
    local py_cmd=""

    for cmd in python3.13 python3.12 python3.11 python3; do
        if command -v "$cmd" &>/dev/null; then
            local version
            version="$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
            local major minor
            major="${version%%.*}"
            minor="${version#*.}"
            if [[ "$major" -ge 3 ]] && [[ "$minor" -ge 11 ]]; then
                py_cmd="$cmd"
                break
            fi
        fi
    done

    if [[ -z "$py_cmd" ]]; then
        echo ""
    else
        echo "$py_cmd"
    fi
}

PYTHON_CMD="$(check_python)"

if [[ -z "$PYTHON_CMD" ]]; then
    error_msg="Python 3.11+ is required but not found."
    distro="$(detect_distro)"
    case "$distro" in
        fedora|rhel|centos)
            error_msg="$error_msg\nInstall with: sudo dnf install python3.11" ;;
        ubuntu|debian|pop)
            error_msg="$error_msg\nInstall with: sudo apt install python3.11" ;;
        arch|manjaro)
            error_msg="$error_msg\nInstall with: sudo pacman -S python" ;;
        *)
            error_msg="$error_msg\nPlease install Python 3.11+ for your distribution." ;;
    esac
    error "$error_msg"
fi

PY_VERSION="$("$PYTHON_CMD" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
success "Python $PY_VERSION ($PYTHON_CMD)"

# -- install method --

INSTALL_DIR="$HOME/.local/bin"
INSTALL_METHOD=""

if command -v pipx &>/dev/null; then
    INSTALL_METHOD="pipx"
    success "pipx found (recommended)"
elif command -v pip3 &>/dev/null; then
    INSTALL_METHOD="pip3"
    info "pipx not found, using pip3"
elif command -v pip &>/dev/null; then
    INSTALL_METHOD="pip"
    info "pipx not found, using pip"
else
    error "Neither pipx nor pip found.\nInstall pip with: $PYTHON_CMD -m ensurepip --user"
fi

# -- install invoq --

info "Installing invoq..."

case "$INSTALL_METHOD" in
    pipx)
        pipx install invoq 2>&1
        ;;
    pip3)
        pip3 install --user invoq 2>&1
        INSTALL_DIR="$("$PYTHON_CMD" -m site --user-base)/bin"
        ;;
    pip)
        pip install --user invoq 2>&1
        INSTALL_DIR="$("$PYTHON_CMD" -m site --user-base)/bin"
        ;;
esac

success "invoq installed"

# -- PATH check --

add_to_path() {
    local dir="$1"
    local rc_file=""

    if [[ -f "$HOME/.zshrc" ]] && [[ "$SHELL" == *"zsh"* ]]; then
        rc_file="$HOME/.zshrc"
    elif [[ -f "$HOME/.bashrc" ]]; then
        rc_file="$HOME/.bashrc"
    elif [[ -f "$HOME/.bash_profile" ]]; then
        rc_file="$HOME/.bash_profile"
    else
        warn "Could not detect shell rc file."
        echo "Add this to your shell config manually:"
        echo "  export PATH=\"$dir:\$PATH\""
        return
    fi

    # Backup
    cp "$rc_file" "${rc_file}.backup.$(date +%s)"

    # Append
    echo '' >> "$rc_file"
    echo '# Added by invoq installer' >> "$rc_file"
    echo "export PATH=\"$dir:\$PATH\"" >> "$rc_file"

    success "Added $dir to PATH in $rc_file"
    info "Restart your terminal or run: source $rc_file"

    # Export for current session
    export PATH="$dir:$PATH"
}

if ! command -v invoq &>/dev/null; then
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        warn "$INSTALL_DIR is not in your PATH"
        echo ""
        read -p "Add to PATH automatically? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            add_to_path "$INSTALL_DIR"
        else
            warn "Skipped PATH update. You may need to add $INSTALL_DIR to your PATH manually."
        fi
    fi
fi

# Verify invoq is now accessible
if command -v invoq &>/dev/null; then
    INVOQ_CMD="invoq"
elif [[ -x "$INSTALL_DIR/invoq" ]]; then
    INVOQ_CMD="$INSTALL_DIR/invoq"
else
    error "invoq was installed but could not be found. Check your PATH."
fi

INSTALLED_VERSION="$("$INVOQ_CMD" --version 2>&1 || true)"
success "Installed: $INSTALLED_VERSION"

# -- launch setup wizard --

echo ""
info "Launching setup wizard..."
echo ""

sleep 1

exec "$INVOQ_CMD" setup
