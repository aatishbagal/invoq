import re


_EMBEDDED_LANGUAGES = frozenset({"awk", "gawk", "mawk", "nawk", "sed", "gsed"})
_INTERPRETERS = re.compile(r"(?:python(?:[23](?:\.\d+)*)?|perl|ruby|node|nodejs|php|lua|luajit)\Z")
_WRAPPERS = frozenset({
    "xargs", "eval", "exec", "command", "builtin", "source", ".", "sudo", "doas",
    "nohup", "nice", "timeout", "watch", "time", "chroot", "busybox", "parallel",
    "sh", "bash", "dash", "zsh", "ksh", "fish",
})
_INFORMATIONAL = frozenset({"--help", "--version"})
_VIEWERS = frozenset({"less", "more", "bat", "man", "info"})
_FIND_ACTIONS = frozenset({"-exec", "-execdir", "-ok", "-okdir", "-delete"})


def check_command_policy(arguments: list[str]) -> str | None:
    command = arguments[0].rsplit("/", 1)[-1]
    args = arguments[1:]
    if command in _WRAPPERS:
        return "Command wrappers and shell execution are blocked"
    informational = len(args) == 1 and args[0] in _INFORMATIONAL
    if command in _EMBEDDED_LANGUAGES and args and not informational:
        return "Embedded programs and in-place editing are blocked"
    if command == "env" and args and not informational:
        return "Environment-based command execution is blocked"
    if command == "find" and any(arg in _FIND_ACTIONS for arg in args):
        return "find execution and deletion actions are blocked"
    if _INTERPRETERS.fullmatch(command) and not informational:
        if any(arg.startswith("-") for arg in args):
            return "Interpreter options and standard-input programs are blocked"
    if command == "sort":
        for arg in args:
            option = arg.split("=", 1)[0]
            if option.startswith("--") and len(option) > 2:
                if "--compress-program".startswith(option):
                    return "External sort helper execution is blocked"
    if command in _VIEWERS and not informational:
        if any(arg.startswith(("-", "+")) for arg in args):
            return "Viewer options and startup commands are blocked"
    return None
