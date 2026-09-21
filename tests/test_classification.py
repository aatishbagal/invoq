import pytest

from invoq.core.parser import extract_base_commands, parse_command
from invoq.core.tiers import CommandTier, SAFE_COMMANDS
from invoq.core.validator import CommandValidator


@pytest.mark.parametrize("command", [
    "awk 'BEGIN { system(\"rm -rf /tmp/x\") }'",
    "awk '{ print $1 }' input",
    "gawk -f program.awk",
    r"find /tmp -exec rm -rf {} \;",
    r'find /tmp -exec r"m" -rf {} \;',
    r'fi"nd" /tmp -ex"ec" echo {} \;',
    "find /tmp -execdir echo {} +",
    r"find /tmp -ok echo {} \;",
    r"find /tmp -okdir echo {} \;",
    "find /tmp -delete",
    "sed -i 's/a/b/' file",
    "sed -i.bak 's/a/b/' file",
    "sed --in-place=.bak 's/a/b/' file",
    "sed 'e echo payload' file",
    "sed -f commands.sed file",
    "perl -e 'system(\"echo payload\")'",
    "perl -we'print 1'",
    "perl -pi -e 's/a/b/' file",
    "python -c 'print(1)'",
    "python3 -Ic'print(1)'",
    "python3 -m module",
    "python3.12 -c 'print(1)'",
    "node --eval='console.log(1)'",
    "ruby -e 'puts 1'",
    "lua -e 'print(1)'",
    "xargs",
    "xargs -I{} echo {}",
    "env python -c 'print(1)'",
    "env -S 'python -c print(1)'",
    "sort --compress-program=helper file",
    "man --pager=helper printf",
    "ls | xargs echo",
    "echo ok\npython -c 'print(1)'",
    "echo ok & python -c 'print(1)'",
])
def test_execution_and_mutation_forms_are_blocked(command):
    result = CommandValidator().validate(command)
    assert result.tier == CommandTier.BLOCKED
    assert not result.allowed


@pytest.mark.parametrize("command", [
    "echo payload > /tmp/file", "echo payload>>/tmp/file",
    "echo payload 2>/tmp/file", "echo payload 1>&2", "echo payload &>/tmp/file",
    "echo payload &>>/tmp/file", "echo payload >|/tmp/file", "cat </tmp/input",
    "cat 3<>/tmp/file", "echo payload 2>&-", ">/tmp/file", "2>/tmp/file echo payload",
])
def test_redirects_require_confirmation(command):
    assert parse_command(command).has_redirect
    result = CommandValidator().validate(command)
    assert result.tier == CommandTier.CONFIRM
    assert result.allowed


@pytest.mark.parametrize("command", [
    "echo '>'", 'echo "2>&1"', r"echo \>", "echo 'x | y; z & q'",
    "echo '$(python -c payload)'", "echo '`python -c payload`'",
])
def test_quoted_or_escaped_operators_are_literal(command):
    parsed = parse_command(command)
    assert not parsed.has_redirect
    assert not parsed.has_pipe
    assert not parsed.has_background
    assert not parsed.has_command_substitution
    assert CommandValidator().validate(command).tier == CommandTier.SAFE


@pytest.mark.parametrize("command", [
    "echo ok\nunknown_tool", "echo ok & unknown_tool",
    "echo ok # comment\nunknown_tool", "echo ok\n# comment\nunknown_tool",
])
def test_all_command_segments_are_inspected(command):
    assert extract_base_commands(command) == ["echo", "unknown_tool"]
    assert not CommandValidator().validate(command).allowed


@pytest.mark.parametrize("command", [
    "echo $(whoami)", 'echo "$(whoami)"', "echo `date`", "echo ${payload}",
    "echo $payload", "echo $((1 + 1))", "cat <(echo payload)", "echo >(cat)",
    "echo 'unterminated", 'echo "unterminated', "echo trailing\\",
    "echo ok ||", "echo ok |", "echo ok &&", "echo ok >>> output",
    "echo ok >", "echo ok <<EOF\npayload\nEOF", "cat <<<payload",
    "echo ok\x00hidden", "echo ok\rhidden", "echo ok ; ; pwd",
    "echo *", "echo {a,b}", "echo ~", "(echo ok)",
    "BASH_ENV=/tmp/payload echo ok", "echo ok; X=value",
])
def test_ambiguous_or_unsupported_shell_syntax_is_blocked(command):
    result = CommandValidator().validate(command)
    assert result.tier == CommandTier.BLOCKED
    assert not result.allowed


@pytest.mark.parametrize("command", ["/tmp/ls", "./echo payload", "/usr/bin/ls"])
def test_explicit_executable_paths_are_not_safe(command):
    assert CommandValidator().validate(command).tier != CommandTier.SAFE


@pytest.mark.parametrize("command", ["LS", "Echo payload"])
def test_command_identity_is_case_sensitive(command):
    assert not CommandValidator().validate(command).allowed


@pytest.mark.parametrize("command", [
    "less", "more", "bat", "awk", "sed", "find", "sort", "uniq", "diff",
    "date", "hostname", "top", "htop", "man", "info", "alias", "history",
    "env", "set", "tree", "file", "lsof", "printf", "test", "uname", "xargs",
])
def test_exec_capable_or_mutating_programs_are_not_safe(command):
    assert command not in SAFE_COMMANDS
    assert CommandValidator().validate(command).tier != CommandTier.SAFE


@pytest.mark.parametrize("command", [
    r'r"m" -rf /tmp/x', "rm '-rf' /tmp/x", r"r\m -r /tmp/x", "rm --force /tmp/x",
    "dd if=/dev/zero of=/dev/sda", "mkfs.ext4 /dev/sda1", "chmod '777' file",
    "chmod -R 777 folder", 'echo x >"/dev/sda"', r"echo x >/dev/s\da",
    "echo x >> /dev/sda", "shred file", ":(){ :|:& };:",
])
def test_canonical_blocks_survive_token_decoding(command):
    result = CommandValidator().validate(command)
    assert result.tier == CommandTier.BLOCKED
    assert not result.allowed


@pytest.mark.parametrize("command", [
    "sort --compress-p=helper file", "sort --com=helper file",
    "man -Hhelper printf", "man -C/tmp/man.conf printf", "man --pag=helper printf",
    "bat --pager=helper file", "bat --config-file=/tmp/bat.conf file",
    "less '+!helper' file", "more '+!helper' file", "info --init-file=/tmp/info.conf",
])
def test_viewer_and_sort_execution_options_are_blocked(command):
    result = CommandValidator().validate(command)
    assert result.tier == CommandTier.BLOCKED
    assert not result.allowed


@pytest.mark.parametrize("command", [
    "find /tmp -name '*.py' -type f", "python script.py", "python --version",
    "awk --help", "less README.md", "sort -o output input", "uniq input output",
    "tree -o output", "date 092100002026", "hostname example", "file -C",
])
def test_reviewable_non_safe_forms_require_confirmation(command):
    result = CommandValidator().validate(command)
    assert result.tier == CommandTier.CONFIRM
    assert result.allowed


@pytest.mark.parametrize("command,expected", [
    ("echo one\necho two", ["echo", "echo"]),
    ("echo one & echo two", ["echo", "echo"]),
    ("echo one # comment\necho two", ["echo", "echo"]),
    ("echo one&&\necho two", ["echo", "echo"]),
    ("ec\\\nho hello", ["echo"]),
    ("cat 2>/tmp/error | grep text", ["cat", "grep"]),
])
def test_literal_shell_segments_are_preserved(command, expected):
    parsed = parse_command(command)
    assert parsed.base_commands == expected
    assert parsed.error is None


@pytest.mark.parametrize("command", ["echo hello", "cat file | grep x | wc -l", "ls && pwd"])
def test_literal_read_only_commands_remain_safe(command):
    result = CommandValidator().validate(command)
    assert result.tier == CommandTier.SAFE
    assert result.allowed
