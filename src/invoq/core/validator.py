from dataclasses import dataclass, field
from typing import List, Optional, Set

from .tiers import CommandTier, get_command_tier
from .blocked_patterns import check_blocked_patterns, BlockedPattern
from .parser import parse_command, ParsedCommand


@dataclass
class ValidationResult:
    allowed: bool
    tier: CommandTier
    reason: str
    commands_found: List[str]
    blocked_pattern: Optional[BlockedPattern] = None
    warnings: List[str] = field(default_factory=list)


# Tier priority for determining overall command risk
_TIER_PRIORITY = {
    CommandTier.SAFE: 0,
    CommandTier.CONFIRM: 1,
    CommandTier.BLOCKED: 2,
    CommandTier.UNKNOWN: 3,
}


class CommandValidator:
    def __init__(self, extension_commands: Optional[Set[str]] = None) -> None:
        """Initialize validator.

        Args:
            extension_commands: Additional commands allowed by extensions.
                               These get CONFIRM tier.
        """
        self._extension_commands: Set[str] = extension_commands or set()

    def add_extension_commands(self, commands: Set[str]) -> None:
        """Add commands from an extension to the allowlist."""
        self._extension_commands.update(commands)

    def validate(self, command: str) -> ValidationResult:
        """Validate a command string.

        Validation order:
        1. Check blocked patterns first (always reject)
        2. Parse command to extract base commands
        3. Check each base command against tiers
        4. Overall tier is the highest risk tier found
        5. If any command is UNKNOWN, entire command is blocked
        """
        stripped = command.strip() if command else ""

        if not stripped:
            return ValidationResult(
                allowed=False,
                tier=CommandTier.UNKNOWN,
                reason="Empty command",
                commands_found=[],
            )

        # 1. Check blocked patterns
        is_blocked, matched_pattern = check_blocked_patterns(stripped)
        if is_blocked:
            return ValidationResult(
                allowed=False,
                tier=CommandTier.BLOCKED,
                reason=f"Blocked: {matched_pattern.description}",
                commands_found=[],
                blocked_pattern=matched_pattern,
            )

        # 2. Parse command
        parsed = parse_command(stripped)

        if not parsed.base_commands:
            return ValidationResult(
                allowed=False,
                tier=CommandTier.UNKNOWN,
                reason="Failed to parse command",
                commands_found=[],
            )

        # 3. Check each base command against tiers
        highest_tier = CommandTier.SAFE
        unknown_cmd: Optional[str] = None

        for cmd in parsed.base_commands:
            tier = get_command_tier(cmd)

            # Check extension commands for UNKNOWN
            if tier == CommandTier.UNKNOWN and cmd.lower() in self._extension_commands:
                tier = CommandTier.CONFIRM

            if _TIER_PRIORITY[tier] > _TIER_PRIORITY[highest_tier]:
                highest_tier = tier
                if tier == CommandTier.UNKNOWN:
                    unknown_cmd = cmd

        # 4. Build warnings
        warnings: List[str] = []
        if "sudo" in stripped.split():
            warnings.append("Command uses sudo (elevated privileges)")
        if parsed.has_redirect:
            warnings.append("Command uses redirect operators")
        if parsed.has_background:
            warnings.append("Command runs in background")
        if parsed.has_command_substitution:
            warnings.append("Command uses command substitution")

        # 5. Determine result
        if highest_tier == CommandTier.UNKNOWN:
            return ValidationResult(
                allowed=False,
                tier=CommandTier.UNKNOWN,
                reason=f"Unknown command: {unknown_cmd}",
                commands_found=parsed.base_commands,
                warnings=warnings,
            )

        if highest_tier == CommandTier.BLOCKED:
            return ValidationResult(
                allowed=False,
                tier=CommandTier.BLOCKED,
                reason="Command is blocked",
                commands_found=parsed.base_commands,
                warnings=warnings,
            )

        if highest_tier == CommandTier.CONFIRM:
            return ValidationResult(
                allowed=True,
                tier=CommandTier.CONFIRM,
                reason="Requires confirmation",
                commands_found=parsed.base_commands,
                warnings=warnings,
            )

        return ValidationResult(
            allowed=True,
            tier=CommandTier.SAFE,
            reason="Safe to execute",
            commands_found=parsed.base_commands,
            warnings=warnings,
        )
