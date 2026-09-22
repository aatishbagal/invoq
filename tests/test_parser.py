import pytest

from invoq.core.parser import parse_command, extract_base_commands, ParsedCommand


pytestmark = pytest.mark.security


class TestExtractBaseCommands:
    # Simple commands
    def test_simple_command(self) -> None:
        assert extract_base_commands("ls") == ["ls"]

    def test_command_with_flags(self) -> None:
        assert extract_base_commands("ls -la") == ["ls"]

    # Pipes
    def test_pipe(self) -> None:
        assert extract_base_commands("a | b | c") == ["a", "b", "c"]

    def test_pipe_with_args(self) -> None:
        assert extract_base_commands("cat file | grep pattern | wc -l") == ["cat", "grep", "wc"]

    # Chains
    def test_and_chain(self) -> None:
        assert extract_base_commands("a && b") == ["a", "b"]

    def test_or_chain(self) -> None:
        assert extract_base_commands("a || b") == ["a", "b"]

    def test_semicolons(self) -> None:
        assert extract_base_commands("a; b; c") == ["a", "b", "c"]

    # Subshells
    def test_subshell(self) -> None:
        assert extract_base_commands("(a && b)") == ["a", "b"]

    def test_command_substitution(self) -> None:
        cmds = extract_base_commands("echo $(whoami)")
        assert "echo" in cmds
        assert "whoami" in cmds

    def test_backticks(self) -> None:
        cmds = extract_base_commands("echo `date`")
        assert "echo" in cmds
        assert "date" in cmds

    # Complex
    def test_complex_mixed(self) -> None:
        cmds = extract_base_commands("cat file | grep x && echo done")
        assert "cat" in cmds
        assert "grep" in cmds
        assert "echo" in cmds

    # Edge cases
    def test_empty_string(self) -> None:
        assert extract_base_commands("") == []

    def test_whitespace(self) -> None:
        assert extract_base_commands("   ") == []

    def test_comment(self) -> None:
        assert extract_base_commands("# this is a comment") == []

    def test_with_path_prefix(self) -> None:
        assert extract_base_commands("/usr/bin/ls -la") == ["ls"]


class TestParseCommand:
    def test_simple_command(self) -> None:
        parsed = parse_command("ls -la")
        assert parsed.original == "ls -la"
        assert parsed.base_commands == ["ls"]
        assert not parsed.has_pipe
        assert not parsed.is_compound

    def test_pipe_detection(self) -> None:
        parsed = parse_command("cat file | grep x")
        assert parsed.has_pipe is True

    def test_redirect_detection(self) -> None:
        parsed = parse_command("ls > file.txt")
        assert parsed.has_redirect is True

    def test_background_detection(self) -> None:
        parsed = parse_command("sleep 10 &")
        assert parsed.has_background is True

    def test_subshell_detection(self) -> None:
        parsed = parse_command("(cd dir && ls)")
        assert parsed.has_subshell is True

    def test_command_substitution_detection(self) -> None:
        parsed = parse_command("echo $(whoami)")
        assert parsed.has_command_substitution is True

    def test_compound_detection(self) -> None:
        parsed = parse_command("ls && pwd")
        assert parsed.is_compound is True

    def test_empty(self) -> None:
        parsed = parse_command("")
        assert parsed.base_commands == []
