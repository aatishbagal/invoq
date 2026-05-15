import re
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass(frozen=True)
class BlockedPattern:
    pattern: re.Pattern
    description: str
    severity: str  # 'critical' or 'high'


BLOCKED_PATTERNS: Tuple[BlockedPattern, ...] = (
    # rm with recursive or force flags
    BlockedPattern(
        pattern=re.compile(r'\brm\s+.*(-[rRf]|-rf|-fr|--recursive|--force)'),
        description="Recursive or forced file deletion",
        severity="critical",
    ),
    # rm root or home
    BlockedPattern(
        pattern=re.compile(r'\brm\s+.*(/|~|\$HOME)\s*$'),
        description="Deletion of root or home directory",
        severity="critical",
    ),
    # dd command
    BlockedPattern(
        pattern=re.compile(r'\bdd\s+'),
        description="Direct disk write operation",
        severity="critical",
    ),
    # mkfs
    BlockedPattern(
        pattern=re.compile(r'\bmkfs\.?'),
        description="Filesystem formatting",
        severity="critical",
    ),
    # chmod 777
    BlockedPattern(
        pattern=re.compile(r'\bchmod\s+777\b'),
        description="World-writable permissions",
        severity="high",
    ),
    # chmod recursive 777
    BlockedPattern(
        pattern=re.compile(r'\bchmod\s+(-R|--recursive)\s+777\b'),
        description="Recursive world-writable permissions",
        severity="critical",
    ),
    # Write to block devices
    BlockedPattern(
        pattern=re.compile(r'>\s*/dev/(sd[a-z]|nvme|hd[a-z]|vd[a-z])'),
        description="Direct write to block device",
        severity="critical",
    ),
    # Fork bombs
    BlockedPattern(
        pattern=re.compile(r':\(\)\s*\{\s*:|:&\s*\};\s*:'),
        description="Fork bomb detected",
        severity="critical",
    ),
    # Shred command
    BlockedPattern(
        pattern=re.compile(r'\bshred\s+'),
        description="Secure file deletion",
        severity="high",
    ),
    # Wget/curl pipe to shell
    BlockedPattern(
        pattern=re.compile(r'(wget|curl).*\|\s*(bash|sh|zsh|sudo)'),
        description="Remote script execution",
        severity="critical",
    ),
    # Sudo with rm -rf
    BlockedPattern(
        pattern=re.compile(r'\bsudo\s+rm\s+.*(-[rRf]|-rf|-fr)'),
        description="Privileged recursive deletion",
        severity="critical",
    ),
    # History clear/deletion
    BlockedPattern(
        pattern=re.compile(r'\bhistory\s+(-c|--clear|-d|--delete)'),
        description="Shell history manipulation",
        severity="high",
    ),
    # Overwrite system files
    BlockedPattern(
        pattern=re.compile(r'>\s*/etc/(passwd|shadow|sudoers|fstab)'),
        description="Overwrite critical system file",
        severity="critical",
    ),
    # Disable firewall
    BlockedPattern(
        pattern=re.compile(r'(ufw|iptables|firewalld)\s+(disable|stop|flush|-F)'),
        description="Firewall disable/flush",
        severity="high",
    ),
)


def _strip_quoted_strings(command: str) -> str:
    """Remove single and double quoted content for pattern matching."""
    result = re.sub(r"'[^']*'", '""', command)
    result = re.sub(r'"[^"]*"', '""', result)
    return result


def check_blocked_patterns(command: str) -> Tuple[bool, Optional[BlockedPattern]]:
    """Check if command matches any blocked pattern.

    Quoted strings are stripped before matching so that arguments like
    echo 'rm -rf /' do not trigger false positives.

    Returns:
        (is_blocked, matched_pattern or None)
    """
    stripped = _strip_quoted_strings(command)
    for bp in BLOCKED_PATTERNS:
        if bp.pattern.search(stripped):
            return (True, bp)
    return (False, None)
