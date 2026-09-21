from .parser import parse_command
from .shell_lexer import tokenize_shell


_REDIRECTS = frozenset({"<", ">", ">>", "<>", ">&", "<&", ">|"})
_CONTROL_WORDS = frozenset({
    "if", "then", "else", "elif", "fi", "while", "until", "do", "done",
    "for", "in", "case", "esac", "select", "function", "time", "coproc", "!",
})


def parse_script_commands(script: str) -> list[str]:
    """Accept only literal, single-line commands joined by &&."""
    if "\n" in script or "\r" in script:
        raise ValueError("Scripts must be a single line joined by &&")

    lexed = tokenize_shell(script)
    if lexed.error or lexed.has_expansion:
        raise ValueError(lexed.error or "Shell expansions are not supported")

    commands: list[str] = []
    start = 0
    previous_end = 0
    for token in lexed.tokens:
        if script[previous_end:token.start].strip():
            raise ValueError("Script comments are not supported")
        previous_end = token.end
        if token.operator:
            if token.value == "&&":
                commands.append(script[start:token.start].strip())
                start = token.end
            elif token.value not in _REDIRECTS:
                raise ValueError(f"Unsupported script operator: {token.value}")
    if script[previous_end:].strip():
        raise ValueError("Script comments are not supported")
    commands.append(script[start:].strip())

    for command in commands:
        parsed = parse_command(command)
        if not command or parsed.error:
            raise ValueError(parsed.error or "Empty script command")
        if any(name in _CONTROL_WORDS for name in parsed.base_commands):
            raise ValueError("Shell control syntax is not supported")
    return commands
