import asyncio
import platform
import subprocess
from unittest.mock import AsyncMock, Mock

import pytest

from invoq.config import Config
from invoq.core.blocked_patterns import check_blocked_patterns
from invoq.core.executor import SafeExecutor
from invoq.core.parser import parse_command
from invoq.core.tiers import CONFIRM_COMMANDS, SAFE_COMMANDS, CommandTier
from invoq.core.validator import CommandValidator
from invoq.mcp.confirmation import ConfirmationHandler
from invoq.mcp.server import InvoqMCPServer
from invoq.mcp.tools.filesystem import get_system_info
from invoq.mcp.types import ToolCall
from invoq.prompts.system_prompts import (
    build_ask_prompt, build_debug_prompt, build_explain_prompt, get_system_context,
)


pytestmark = pytest.mark.security

DISK_COMMANDS = [
    "diskutil eraseDisk APFS Empty GPT disk2",
    "'diskutil' 'eraseDisk' APFS Empty GPT disk2",
    'diskutil erase"Disk" APFS Empty GPT disk2',
    "diskutil eraseVolume APFS Empty disk2s1",
    r"diskutil erase\Volume APFS Empty disk2s1",
    "/usr/sbin/diskutil partitionDisk disk2 GPT APFS Empty 100%",
    "'/usr/sbin/diskutil' 'partitionDisk' disk2 GPT APFS Empty 100%",
    "diskutil zeroDisk force short disk2",
    r"disk\util zero\Disk force short disk2",
    "diskutil\tzeroDisk\tdisk2",
    "diskutil eraseOptical quick disk2",
    "diskutil 'eraseOptical' quick disk2",
    "diskutil ERASEDISK APFS Empty GPT disk2",
    "/usr/sbin/DISKUTIL eraseDisk APFS Empty GPT disk2",
    "'/usr/sbin/DisKuTiL' 'zeroDisk' disk2",
    "diskutil apfs eraseVolume disk2s1 -name Empty",
    "diskutil 'apfs' 'eraseVolume' disk2s1 -name Empty",
    "newfs_hfs disk2s1",
    "'newfs_hfs' disk2s1",
    "newfs_apfs disk2",
    r"newfs_\apfs disk2",
    "newfs_msdos disk2s1",
    "/sbin/newfs_msdos 'disk2s1'",
    "newfs_exfat disk2s1",
    "newfs_'exfat' disk2s1",
    "newfs_udf disk2s1",
    r"newfs_\udf disk2s1",
    "newfs_custom-format disk2s1",
    "'newfs_custom-format' disk2s1",
    "/sbin/NEWFS_APFS disk2",
    "'NewFs_hfs' disk2s1",
    "/sbin/newfs_hfs -v Empty /dev/rdisk2s1",
    "'/sbin/newfs_apfs' '/dev/disk2'",
    "newfs_msdos -F 32 '/dev/rdisk2s1'",
]

DEVICE_WRITES = [
    "echo payload > /dev/disk0",
    "echo payload >'/dev/disk0'",
    "echo payload >> /dev/rdisk12s3",
    r"echo payload >> /dev/rdi\sk12s3",
    "echo payload >| /dev/disk2s1",
    "echo payload 2> /dev/rdisk2",
    "echo payload &> /dev/disk2",
    "echo payload &>> /dev/rdisk2",
    "cat 3<> '/dev/disk2s1'",
    ">/dev/rdisk2",
    "echo payload >/dev/./disk2",
    "echo payload >/dev//rdisk2",
    "echo payload >//dev/disk2",
    "echo payload >/dev/../dev/rdisk2",
    "cp image.bin /dev/disk2",
    "cp image.bin '/dev/rdisk2s1'",
    "cp image.bin /dev/./disk2",
    "curl --output=/dev/disk2 https://example.invalid/image",
    "curl -o/dev/rdisk2 https://example.invalid/image",
    "curl --output '/dev/disk2' https://example.invalid/image",
    "tee /dev/disk2",
    "tee -a '/dev/rdisk2'",
]

BSD_BLOCKED = [
    "sed -i '' 's/old/new/' file",
    'sed -i "" -e "s/old/new/" file',
    "sed -i .bak 's/old/new/' file",
    "sed -i.bak 's/old/new/' file",
    "sed -I '' 's/old/new/' first second",
    "sed -E -i '' -f script.sed file",
    r"s\ed '-i' '' 's/old/new/' file",
    "/usr/bin/sed -i '' 's/old/new/' file",
    r"find -x . -exec echo '{}' \;",
    "find -E . -exec echo '{}' +",
    r"find . -execdir echo '{}' \;",
    "find . -execdir echo '{}' +",
    r"find . -ok echo '{}' \;",
    r"find . -okdir echo '{}' \;",
    "find -d . -type f -delete",
    "find -f . -delete",
    r"fi\nd . -de\lete",
    "/usr/bin/find . '-exec' echo '{}' ';'",
    "awk 'BEGIN { system(\"echo payload\") }'",
    "awk 'BEGIN { print \"payload\" > \"output\" }'",
    "awk -f script.awk input",
    r"a\wk 'BEGIN { system(\"echo payload\") }'",
    "/usr/bin/awk 'BEGIN { system(\"echo payload\") }'",
]


@pytest.fixture(autouse=True)
def no_processes(monkeypatch):
    shell = AsyncMock(side_effect=AssertionError("Security payload must never execute"))
    direct = AsyncMock(side_effect=AssertionError("Security payload must never execute"))
    popen = Mock(side_effect=AssertionError("Security payload must never execute"))
    monkeypatch.setattr(asyncio, "create_subprocess_shell", shell)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", direct)
    monkeypatch.setattr(subprocess, "Popen", popen)
    yield
    shell.assert_not_called()
    direct.assert_not_called()
    popen.assert_not_called()


@pytest.mark.parametrize("system", ["Linux", "Darwin"])
@pytest.mark.parametrize("command", DISK_COMMANDS + DEVICE_WRITES)
def test_macos_operations_are_blocked_on_every_host(monkeypatch, system, command):
    monkeypatch.setattr(platform, "system", lambda: system)
    parsed = parse_command(command)
    assert parsed.error is None
    validator = CommandValidator(extension_commands=set(parsed.base_commands))

    result = validator.validate(command)

    assert not result.allowed
    assert result.tier == CommandTier.BLOCKED
    assert result.blocked_pattern is not None
    assert result.blocked_pattern.severity == "critical"


@pytest.mark.parametrize("command", [
    "diskutil eraseDisk APFS Empty disk2",
    "diskutil eraseVolume APFS Empty disk2s1",
    "diskutil partitionDisk disk2 GPT APFS Empty 100%",
    "diskutil zeroDisk disk2",
    "newfs_hfs disk2s1", "newfs_apfs disk2", "newfs_msdos disk2s1",
    "echo payload >/dev/disk0", "echo payload >/dev/rdisk0s1",
])
def test_canonical_macos_operations_have_explicit_patterns(command):
    blocked, pattern = check_blocked_patterns(command)
    assert blocked
    assert pattern.severity == "critical"


@pytest.mark.parametrize("command", BSD_BLOCKED)
def test_bsd_programs_and_find_actions_stay_blocked(command):
    result = CommandValidator().validate(command)
    assert not result.allowed
    assert result.tier == CommandTier.BLOCKED


@pytest.mark.parametrize("command", [
    "dd if=/dev/zero of=/dev/disk2 bs=1m",
    "'dd' 'if=/dev/zero' 'of=/dev/rdisk2' bs=1m",
    "cat '/dev/disk2'", "cat < '/dev/rdisk2s1'",
])
def test_raw_device_access_is_denied(command):
    result = CommandValidator().validate(command)
    assert not result.allowed
    assert result.tier == CommandTier.BLOCKED


@pytest.mark.parametrize("command", [
    "find -E . -regex '.*[.]py' -print",
    "find -x . -type f -print", "find -f . -name '*.py'",
    "echo payload > output", "echo payload >> 'output file'",
    "echo payload >| output", "echo payload 2> output",
    "echo payload &> output", "cat 3<> output",
])
def test_bsd_queries_and_ordinary_redirects_require_confirmation(command):
    result = CommandValidator().validate(command)
    assert result.allowed
    assert result.tier == CommandTier.CONFIRM


@pytest.mark.parametrize("command", [
    "echo 'diskutil eraseDisk APFS Empty disk2'",
    "echo 'newfs_hfs disk2s1'", "echo '> /dev/disk2'",
    "echo payload > ./disk2", "echo payload >/tmp/dev/disk2",
    "echo payload >/dev/disk-image", "echo payload >/dev/rdisk-not-a-device",
])
def test_literal_examples_and_unrelated_paths_are_not_blocked(command):
    result = CommandValidator().validate(command)
    assert result.allowed
    assert result.tier in {CommandTier.SAFE, CommandTier.CONFIRM}


@pytest.mark.parametrize("command", [
    "pbcopy", "pbpaste", "open .", "launchctl list", "defaults read",
    "softwareupdate --list", "diskutil list",
])
def test_macos_conveniences_remain_unclassified(command):
    name = command.split()[0]
    assert name not in SAFE_COMMANDS | CONFIRM_COMMANDS
    assert not CommandValidator().validate(command).allowed


@pytest.mark.parametrize("tool,field", [
    ("execute_command", "command"), ("execute_script", "script"),
])
@pytest.mark.parametrize("command", DISK_COMMANDS + DEVICE_WRITES)
def test_macos_payload_cannot_reach_confirmation_or_execution(monkeypatch, tool, field, command):
    validator = CommandValidator(extension_commands=set(parse_command(command).base_commands))
    history = Mock()
    executor = SafeExecutor(validator, Config(), history=history)
    handler = ConfirmationHandler(validator)
    confirm = AsyncMock()
    script_confirm = AsyncMock()
    monkeypatch.setattr(handler, "request_confirmation", confirm)
    monkeypatch.setattr(handler, "request_script_confirmation", script_confirm)
    server = InvoqMCPServer(executor=executor, history=history, confirmation_handler=handler)

    result = asyncio.run(server.handle_tool_call(ToolCall(tool, {field: command}, "macos")))

    assert not result.success
    assert "BLOCKED" in result.error
    confirm.assert_not_awaited()
    script_confirm.assert_not_awaited()


def test_macos_context_and_prompts_identify_bsd_userland(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "release", lambda: "24.0.0")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("15.0", ("", "", ""), "arm64"))
    context = get_system_context()
    assert "macOS 15.0" in context["os_info"]
    assert "Darwin 24.0.0" in context["os_info"]
    assert "BSD" in context["os_info"]
    for prompt in [build_ask_prompt(), build_explain_prompt(), build_debug_prompt("ls", 1, "error")]:
        assert "macOS" in prompt and "BSD" in prompt
        assert "expert Linux" not in prompt


def test_macos_system_info_distinguishes_product_from_kernel(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "release", lambda: "24.0.0")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("15.0", ("", "", ""), "arm64"))
    result = asyncio.run(get_system_info())
    assert result.success
    assert "os: Darwin" in result.output
    assert "os_release: 24.0.0" in result.output
    assert "os_name: macOS" in result.output
    assert "macos_version: 15.0" in result.output
    assert "userland: BSD" in result.output


@pytest.mark.parametrize("system", ["Linux", "Windows"])
def test_non_macos_context_preserves_detection(monkeypatch, system):
    monkeypatch.setattr(platform, "system", lambda: system)
    monkeypatch.setattr(platform, "release", lambda: "test-kernel")
    monkeypatch.setattr(platform, "mac_ver", Mock(side_effect=AssertionError("Not macOS")))
    assert get_system_context()["os_info"] == f"{system} test-kernel"
    result = asyncio.run(get_system_info())
    assert result.success
    assert f"os: {system}" in result.output
    assert "userland: BSD" not in result.output
