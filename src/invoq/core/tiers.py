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
    "cat", "head", "tail",
    # Directory
    "ls", "pwd", "locate", "which", "whereis",
    # Text processing
    "grep", "cut", "wc", "tr",
    # System info
    "whoami", "id", "groups", "cal", "uptime",
    "df", "du", "free", "ps", "who", "w",
    # File info
    "stat", "md5sum", "sha256sum",
    # Shell
    "echo", "true", "false", "expr", "seq", "yes",
    # Misc
    "help", "type", "printenv",
})

# Confirm commands - have side effects, need user confirmation
CONFIRM_COMMANDS: FrozenSet[str] = frozenset({
    # Programs with execution, mutation, or interactive capabilities
    "awk", "gawk", "mawk", "nawk", "sed", "gsed", "find", "xargs",
    "less", "more", "bat", "sort", "uniq", "diff", "tree", "file", "lsof",
    "date", "hostname", "uname", "top", "htop", "man", "info",
    "alias", "history", "env", "set", "printf", "test",
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
    "python", "python2", "python3", "node", "nodejs", "ruby", "perl", "php",
    "java", "lua", "luajit",
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
    cmd = command.strip()
    if cmd in SAFE_COMMANDS:
        return CommandTier.SAFE
    if cmd in CONFIRM_COMMANDS:
        return CommandTier.CONFIRM
    return CommandTier.UNKNOWN
