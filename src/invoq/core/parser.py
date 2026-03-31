import re
import shlex
from dataclasses import dataclass
from typing import List


@dataclass
class ParsedCommand:
    original: str
    base_commands: List[str]
    has_pipe: bool
    has_redirect: bool
    has_background: bool
    has_subshell: bool
    has_command_substitution: bool
    is_compound: bool


def extract_base_commands(command: str) -> List[str]:
    """Extract base command names from a shell command string."""
    if not command or not command.strip():
        return []

    cmd = command.strip()

    # Strip leading comments
    if cmd.startswith("#"):
        return []

    # Remove command substitutions and capture inner commands
    inner_commands: List[str] = []

    # Extract $(...) substitutions
    def extract_subshell(text: str) -> str:
        result = text
        while True:
            match = re.search(r'\$\(([^)]+)\)', result)
            if not match:
                break
            inner_commands.extend(extract_base_commands(match.group(1)))
            result = result[:match.start()] + "___SUB___" + result[match.end():]
        return result

    # Extract backtick substitutions
    def extract_backticks(text: str) -> str:
        result = text
        while True:
            match = re.search(r'`([^`]+)`', result)
            if not match:
                break
            inner_commands.extend(extract_base_commands(match.group(1)))
            result = result[:match.start()] + "___SUB___" + result[match.end():]
        return result

    cmd = extract_subshell(cmd)
    cmd = extract_backticks(cmd)

    # Strip subshell parentheses
    cmd = cmd.strip()
    while cmd.startswith("(") and cmd.endswith(")"):
        cmd = cmd[1:-1].strip()

    # Split on pipes, &&, ||, and semicolons (outside quotes)
    segments = _split_on_operators(cmd)

    commands: List[str] = []
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue

        # Remove background operator
        segment = segment.rstrip("&").strip()

        # Remove redirects
        segment = re.sub(r'\d*[<>]+\s*\S+', '', segment).strip()

        if not segment:
            continue

        # Extract base command
        base = _get_base_command(segment)
        if base:
            commands.append(base)

    commands.extend(inner_commands)
    return commands


def _split_on_operators(cmd: str) -> List[str]:
    """Split command string on |, &&, ||, ; respecting quotes."""
    segments: List[str] = []
    current: List[str] = []
    in_single_quote = False
    in_double_quote = False
    i = 0

    while i < len(cmd):
        char = cmd[i]

        # Handle escapes
        if char == "\\" and i + 1 < len(cmd) and not in_single_quote:
            current.append(char)
            current.append(cmd[i + 1])
            i += 2
            continue

        # Handle quotes
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            current.append(char)
            i += 1
            continue

        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current.append(char)
            i += 1
            continue

        if in_single_quote or in_double_quote:
            current.append(char)
            i += 1
            continue

        # Check operators (outside quotes)
        if char == "|":
            if i + 1 < len(cmd) and cmd[i + 1] == "|":
                # ||
                segments.append("".join(current))
                current = []
                i += 2
                continue
            else:
                # pipe
                segments.append("".join(current))
                current = []
                i += 1
                continue

        if char == "&":
            if i + 1 < len(cmd) and cmd[i + 1] == "&":
                # &&
                segments.append("".join(current))
                current = []
                i += 2
                continue
            else:
                # background &, keep in segment
                current.append(char)
                i += 1
                continue

        if char == ";":
            segments.append("".join(current))
            current = []
            i += 1
            continue

        current.append(char)
        i += 1

    if current:
        segments.append("".join(current))

    return segments


def _get_base_command(segment: str) -> str:
    """Extract the base command name from a single command segment."""
    segment = segment.strip()
    if not segment:
        return ""

    # Try shlex first
    try:
        tokens = shlex.split(segment)
    except ValueError:
        # Fallback: split on whitespace
        tokens = segment.split()

    if not tokens:
        return ""

    # Skip env var assignments (FOO=bar cmd)
    idx = 0
    while idx < len(tokens) and re.match(r'^[A-Za-z_]\w*=', tokens[idx]):
        idx += 1

    if idx >= len(tokens):
        return ""

    cmd = tokens[idx]

    # Strip path prefix
    if "/" in cmd:
        cmd = cmd.rsplit("/", 1)[-1]

    return cmd


def parse_command(command: str) -> ParsedCommand:
    """Parse a command string into a ParsedCommand."""
    original = command
    stripped = command.strip() if command else ""

    base_commands = extract_base_commands(stripped)

    return ParsedCommand(
        original=original,
        base_commands=base_commands,
        has_pipe=bool(re.search(r'(?<![|])\|(?![|])', stripped)) if stripped else False,
        has_redirect=bool(re.search(r'[<>]', stripped)) if stripped else False,
        has_background=bool(stripped and stripped.rstrip().endswith("&") and not stripped.rstrip().endswith("&&")),
        has_subshell=bool(re.search(r'[()]', stripped)) if stripped else False,
        has_command_substitution=bool(re.search(r'\$\(|`', stripped)) if stripped else False,
        is_compound=bool(re.search(r'&&|\|\||;', stripped)) if stripped else False,
    )
