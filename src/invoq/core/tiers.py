from enum import Enum
from typing import FrozenSet


class CommandTier(Enum):
    SAFE = "safe"
    CONFIRM = "confirm"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


# Safe commands - read-only, informational, no side effects
SAFE_COMMANDS: FrozenSet[str] = frozenset({
    # File viewing
    "cat", "head", "tail", "less", "more", "bat",
    # Directory
    "ls", "pwd", "tree", "find", "locate", "which", "whereis",
    # Text processing
    "grep", "awk", "sed", "cut", "sort", "uniq", "wc", "diff", "tr",
    # System info
    "whoami", "id", "groups", "date", "cal", "uptime", "uname",
    "hostname", "df", "du", "free", "top", "htop", "ps", "who", "w",
    # File info
    "file", "stat", "lsof", "md5sum", "sha256sum",
    # Shell
    "echo", "printf", "true", "false", "test", "expr", "seq", "yes",
    # Misc
    "man", "help", "info", "type", "alias", "history", "env", "printenv", "set",
})

# Confirm commands - have side effects, need user confirmation
CONFIRM_COMMANDS: FrozenSet[str] = frozenset({
    # Version control
    "git", "svn", "hg",
    # Package managers
    "pip", "pip3", "pipx", "npm", "npx", "yarn", "pnpm",
    "cargo", "gem", "go", "composer",
    # Build tools
    "make", "cmake", "ninja", "meson", "gcc", "g++", "clang",
    "rustc", "javac",
    # Containers
    "docker", "podman", "kubectl", "docker-compose",
    # Languages
    "python", "python3", "node", "ruby", "perl", "php", "java", "lua",
    # Network
    "curl", "wget", "ssh", "scp", "rsync", "nc", "netcat",
    "ping", "traceroute", "dig", "nslookup", "host",
    # Archives
    "tar", "gzip", "gunzip", "bzip2", "xz", "zip", "unzip", "7z",
    # File ops
    "cp", "mv", "mkdir", "touch", "ln", "chmod", "chown", "chgrp",
    # Editors
    "vim", "nvim", "nano", "vi", "emacs", "code",
    # System
    "systemctl", "journalctl", "service", "crontab",
})


def get_command_tier(command: str) -> CommandTier:
    """Get the tier for a base command name."""
    cmd = command.strip().lower()
    if cmd in SAFE_COMMANDS:
        return CommandTier.SAFE
    if cmd in CONFIRM_COMMANDS:
        return CommandTier.CONFIRM
    return CommandTier.UNKNOWN
