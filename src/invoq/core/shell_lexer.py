from dataclasses import dataclass, field


@dataclass
class ShellToken:
    value: str
    operator: bool
    start: int
    end: int
    plain: bool = True


@dataclass
class ShellTokens:
    tokens: list[ShellToken] = field(default_factory=list)
    has_expansion: bool = False
    has_command_substitution: bool = False
    error: str | None = None


_OPERATORS = (
    ";;&", "&>>", "<<<", "<<-", "&&", "||", ">>", "<<", "<>",
    ">&", "<&", ">|", "&>", "|&", ";;", ";&", "|", "&", ";", "<", ">",
    "(", ")", "`", "\n",
)


def tokenize_shell(command: str) -> ShellTokens:
    result = ShellTokens()
    if any(ord(char) < 32 and char not in "\t\n" for char in command):
        result.error = "Unsupported control character"
    word: list[str] = []
    start: int | None = None
    quote: str | None = None
    plain = True
    index = 0

    def finish_word(end: int) -> None:
        nonlocal start, plain
        if start is not None:
            result.tokens.append(ShellToken("".join(word), False, start, end, plain))
        word.clear()
        start = None
        plain = True

    while index < len(command):
        char = command[index]
        if quote == "'":
            if char == "'":
                quote = None
            else:
                word.append(char)
            index += 1
            continue
        if char == "\\":
            if index + 1 == len(command):
                result.error = "Incomplete escape"
                break
            following = command[index + 1]
            if following == "\n":
                index += 2
                continue
            if start is None:
                start = index
            plain = False
            if quote == '"' and following not in '$`"\\':
                word.append("\\")
            word.append(following)
            index += 2
            continue
        if char == quote:
            quote = None
            index += 1
            continue
        if char == "$" or char == "`":
            result.has_expansion = True
            if char == "`" or command[index:index + 2] == "$(":
                result.has_command_substitution = True
        if quote == '"':
            word.append(char)
            index += 1
            continue
        if char in "'\"":
            if start is None:
                start = index
            plain = False
            quote = char
            index += 1
            continue
        if char == "#" and start is None:
            end = command.find("\n", index)
            index = len(command) if end == -1 else end
            continue
        if char in " \t":
            finish_word(index)
            index += 1
            continue
        operator = next((op for op in _OPERATORS if command.startswith(op, index)), None)
        if operator is not None:
            finish_word(index)
            result.tokens.append(ShellToken(operator, True, index, index + len(operator)))
            index += len(operator)
            continue
        if char in "*?[]{}~":
            result.has_expansion = True
        if start is None:
            start = index
        word.append(char)
        index += 1

    finish_word(index)
    if quote is not None:
        result.error = "Unterminated quote"
    return result
