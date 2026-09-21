import re
from dataclasses import dataclass, field
from typing import List

from .shell_lexer import tokenize_shell


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
    commands: list[list[str]] = field(default_factory=list)
    redirects: list[tuple[str, str]] = field(default_factory=list)
    error: str | None = None
    has_expansion: bool = False
    has_assignment: bool = False
    has_explicit_path: bool = False


_REDIRECTS = frozenset({"<", ">", ">>", "<>", ">&", "<&", ">|", "&>", "&>>"})
_SEPARATORS = frozenset({"|", "&&", "||", ";", "&", "\n"})
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def extract_base_commands(command: str) -> List[str]:
    """Extract command names; callers must also check parse errors before execution."""
    return parse_command(command).base_commands


def parse_command(command: str) -> ParsedCommand:
    """Parse literal POSIX commands, separators and redirects; reject other syntax."""
    lexed = tokenize_shell(command or "")
    parsed = ParsedCommand(
        original=command, base_commands=[], has_pipe=False, has_redirect=False,
        has_background=False, has_subshell=False,
        has_command_substitution=lexed.has_command_substitution, is_compound=False,
        has_expansion=lexed.has_expansion, error=lexed.error,
    )
    words: list[str] = []
    segment_has_redirect = False
    requires_command = False

    def finish_segment() -> bool:
        nonlocal segment_has_redirect
        present = bool(words) or segment_has_redirect
        while words and _ASSIGNMENT.match(words[0]):
            parsed.has_assignment = True
            words.pop(0)
        if words:
            parsed.commands.append(words.copy())
            executable = words[0]
            parsed.has_explicit_path |= "/" in executable
            parsed.base_commands.append(executable.rsplit("/", 1)[-1])
        words.clear()
        segment_has_redirect = False
        return present

    tokens = lexed.tokens
    index = 0
    while index < len(tokens):
        token = tokens[index]
        value = token.value
        if not token.operator:
            if (token.plain and value.isascii() and value.isdigit()
                    and index + 1 < len(tokens)
                    and tokens[index + 1].operator
                    and tokens[index + 1].value in _REDIRECTS
                    and token.end == tokens[index + 1].start):
                index += 1
                continue
            words.append(value)
            index += 1
            continue
        if value in _REDIRECTS:
            parsed.has_redirect = True
            segment_has_redirect = True
            if index + 1 >= len(tokens) or tokens[index + 1].operator:
                parsed.error = "Redirect requires a literal target"
                index += 1
                continue
            target = tokens[index + 1].value
            parsed.redirects.append((value, target))
            index += 2
            continue
        if value in _SEPARATORS:
            parsed.has_pipe |= value == "|"
            parsed.has_background |= value == "&"
            parsed.is_compound |= value in {"&&", "||", ";", "&", "\n"}
            present = finish_segment()
            if not present and value != "\n":
                parsed.error = "Operator without a command"
            if present or value != "\n":
                requires_command = value in {"|", "&&", "||"}
            index += 1
            continue
        parsed.has_subshell |= value in {"(", ")"}
        parsed.has_redirect |= "<" in value or ">" in value
        parsed.error = f"Unsupported shell operator: {value}"
        finish_segment()
        index += 1

    if not finish_segment() and requires_command:
        parsed.error = "Incomplete command chain"
    if parsed.has_expansion:
        parsed.error = "Shell expansions are not supported"
    if parsed.has_assignment:
        parsed.error = "Shell assignments are not supported"
    return parsed
