"""Fail closed: only understood literal commands may be SAFE.

Unsupported syntax is BLOCKED; unknown executables are denied. Redirection,
background execution, explicit executable paths and stateful tools require
confirmation. Command names alone never override argument or syntax policy.
"""

import shlex
from dataclasses import dataclass, field
from typing import List, Optional, Set

from .tiers import CommandTier, get_command_tier
from .blocked_patterns import check_blocked_patterns, BlockedPattern
from .command_policy import check_command_policy
from .parser import parse_command


@dataclass
class ValidationResult:
    allowed: bool
    tier: CommandTier
    reason: str
    commands_found: List[str]
    blocked_pattern: Optional[BlockedPattern] = None
    warnings: List[str] = field(default_factory=list)


_TIER_PRIORITY = {
    CommandTier.SAFE: 0,
    CommandTier.CONFIRM: 1,
    CommandTier.BLOCKED: 2,
    CommandTier.UNKNOWN: 3,
}


class CommandValidator:
    def __init__(self, extension_commands: Optional[Set[str]] = None) -> None:
        self._extension_commands: Set[str] = extension_commands or set()

    def add_extension_commands(self, commands: Set[str]) -> None:
        self._extension_commands.update(commands)

    def validate(self, command: str) -> ValidationResult:
        stripped = command.strip() if command else ""
        if not stripped:
            return ValidationResult(False, CommandTier.UNKNOWN, "Empty command", [])

        is_blocked, matched_pattern = check_blocked_patterns(stripped)
        if is_blocked:
            return ValidationResult(
                allowed=False, tier=CommandTier.BLOCKED,
                reason=f"Blocked: {matched_pattern.description}",
                commands_found=[], blocked_pattern=matched_pattern,
            )

        parsed = parse_command(command)
        warnings: List[str] = []
        if "sudo" in parsed.base_commands:
            warnings.append("Running with elevated privileges")
        for arguments in parsed.commands:
            if arguments[0].rsplit("/", 1)[-1] == "git" and any(
                arg in {"--force", "-f"} for arg in arguments[1:]
            ):
                warnings.append("Force flag may overwrite data")
            if any(arg.startswith(("/etc", "/usr")) for arg in arguments[1:]):
                warnings.append("Modifying system files")
        if parsed.has_redirect:
            warnings.append("Command uses redirect operators")
        if parsed.has_background:
            warnings.append("Command runs in background")
        if parsed.has_command_substitution:
            warnings.append("Command uses command substitution")

        if parsed.error:
            return ValidationResult(
                False, CommandTier.BLOCKED, parsed.error, parsed.base_commands,
                warnings=warnings,
            )

        for arguments in parsed.commands:
            normalized = [arguments[0].rsplit("/", 1)[-1], *arguments[1:]]
            is_blocked, matched_pattern = check_blocked_patterns(shlex.join(normalized))
            reason = check_command_policy(arguments)
            if is_blocked or reason:
                return ValidationResult(
                    allowed=False, tier=CommandTier.BLOCKED,
                    reason=f"Blocked: {matched_pattern.description}" if is_blocked else reason,
                    commands_found=parsed.base_commands,
                    blocked_pattern=matched_pattern, warnings=warnings,
                )

        for operator, target in parsed.redirects:
            if ">" in operator:
                is_blocked, matched_pattern = check_blocked_patterns(f">{target}")
                if is_blocked:
                    return ValidationResult(
                        False, CommandTier.BLOCKED,
                        f"Blocked: {matched_pattern.description}", parsed.base_commands,
                        blocked_pattern=matched_pattern, warnings=warnings,
                    )

        if not parsed.base_commands and not parsed.has_redirect:
            return ValidationResult(False, CommandTier.UNKNOWN, "No command found", [])

        highest_tier = (
            CommandTier.CONFIRM
            if parsed.has_redirect or parsed.has_background or parsed.has_explicit_path
            else CommandTier.SAFE
        )
        unknown_cmd: Optional[str] = None
        for cmd in parsed.base_commands:
            tier = get_command_tier(cmd)
            if tier == CommandTier.UNKNOWN and cmd in self._extension_commands:
                tier = CommandTier.CONFIRM
            if _TIER_PRIORITY[tier] > _TIER_PRIORITY[highest_tier]:
                highest_tier = tier
                if tier == CommandTier.UNKNOWN:
                    unknown_cmd = cmd

        if highest_tier == CommandTier.UNKNOWN:
            return ValidationResult(
                False, highest_tier, f"Unknown command: {unknown_cmd}",
                parsed.base_commands, warnings=warnings,
            )
        if highest_tier == CommandTier.BLOCKED:
            return ValidationResult(
                False, highest_tier, "Command is blocked", parsed.base_commands,
                warnings=warnings,
            )
        return ValidationResult(
            allowed=True, tier=highest_tier,
            reason="Requires confirmation" if highest_tier == CommandTier.CONFIRM else "Safe to execute",
            commands_found=parsed.base_commands, warnings=warnings,
        )
