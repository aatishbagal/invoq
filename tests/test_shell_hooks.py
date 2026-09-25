import json
import os
from pathlib import Path
import time
import shlex
import shutil
import subprocess

import pytest

from invoq.shell import installation
from invoq.shell.installation import SOURCE_LINE
from invoq.shell.hooks import bash_hook, zsh_hook


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("SHELL", "/bin/bash")
    return tmp_path


@pytest.mark.parametrize("shell,rc_name", [("bash", ".bashrc"), ("zsh", ".zshrc")])
def test_install_uninstall_round_trip(home, monkeypatch, shell, rc_name):
    monkeypatch.setenv("SHELL", f"/bin/{shell}")
    rc = home / rc_name
    original = "# My shell settings\nexport EDITOR=vi\n"
    rc.write_text(original)

    installation.install_shell_hooks()
    installation.install_shell_hooks()

    script = home / ".config/invoq/shell_hook.sh"
    assert script.is_file()
    assert rc.read_text() == original + SOURCE_LINE + "\n"
    installed = installation.get_shell_status()
    assert installed.script_exists
    assert installed.sourced_from == (rc,)

    log = home / ".local/share/invoq/shell_failures.log"
    log.parent.mkdir(parents=True)
    log.write_text('{"command":"false"}\n')
    installation.uninstall_shell_hooks()
    installation.uninstall_shell_hooks()

    assert rc.read_text() == original
    assert not script.exists()
    assert len(list((script.parent / "deprecated").glob("shell_hook-*.sh"))) == 1
    assert log.read_text() == '{"command":"false"}\n'
    assert not installation.get_shell_status().script_exists
    assert not installation.get_shell_status().sourced_from


def test_install_preserves_rc_without_final_newline(home):
    rc = home / ".bashrc"
    rc.write_text("export EDITOR=vi")
    installation.install_shell_hooks()
    assert rc.read_text() == "export EDITOR=vi\n" + SOURCE_LINE + "\n"


def test_switching_shell_requires_uninstall_before_replacing_script(home, monkeypatch):
    installation.install_shell_hooks()
    script = home / ".config/invoq/shell_hook.sh"
    original = script.read_text()
    monkeypatch.setenv("SHELL", "/bin/zsh")
    with pytest.raises(ValueError, match="before switching shells"):
        installation.install_shell_hooks()
    assert script.read_text() == original
    assert not (home / ".zshrc").exists()
    installation.uninstall_shell_hooks()
    installation.install_shell_hooks()
    assert script.read_text().startswith("# invoq shell hook: zsh")


def test_uninstall_cleans_both_rc_files_and_preserves_other_sources(home):
    other = 'source "$HOME/my_shell_hook.sh"\n'
    for name in (".bashrc", ".zshrc"):
        (home / name).write_text(SOURCE_LINE + "\n" + other)
    installation.uninstall_shell_hooks()
    for name in (".bashrc", ".zshrc"):
        assert (home / name).read_text() == other


@pytest.mark.parametrize("shell", ["", "/bin/fish", "/bin/sh"])
def test_unsupported_shell_does_not_write(home, monkeypatch, shell):
    monkeypatch.setenv("SHELL", shell)
    with pytest.raises(ValueError, match="bash and zsh"):
        installation.install_shell_hooks()
    assert list(home.iterdir()) == []


@pytest.mark.parametrize("age,content,recent", [(0, "", False), (0, "{}\n", True), (90000, "{}\n", False)])
def test_status_reports_log_activity(home, age, content, recent):
    log = home / ".local/share/invoq/shell_failures.log"
    log.parent.mkdir(parents=True)
    log.write_text(content)
    timestamp = time.time() - age
    os.utime(log, (timestamp, timestamp))
    status = installation.get_shell_status()
    assert status.log_exists
    assert status.log_recent is recent


def test_status_does_not_create_files(home):
    assert not installation.get_shell_status().script_exists
    assert list(home.iterdir()) == []


@pytest.mark.parametrize("generate,shell", [(bash_hook, "bash"), (zsh_hook, "zsh")])
def test_generated_hook_content_and_syntax(home, generate, shell):
    content = generate()
    assert f"# invoq shell hook: {shell}" in content
    assert "exec 2>" not in content
    assert "tee " not in content
    assert "PS1=" not in content
    assert "alias " not in content
    if shell == "bash":
        assert " ERR" in content
        assert " DEBUG" not in content
    else:
        assert "add-zsh-hook preexec _invoq_preexec" in content
        assert "add-zsh-hook precmd _invoq_precmd" in content
    binary = shutil.which(shell)
    if binary is None or os.name == "nt":
        pytest.skip(f"Native {shell} is unavailable")
    result = subprocess.run([binary, "-n"], input=content, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def run_shell(home, shell, commands):
    binary = shutil.which(shell)
    if binary is None or os.name == "nt":
        pytest.skip(f"Native {shell} is unavailable")
    script = home / "hook.sh"
    script.write_text(bash_hook() if shell == "bash" else zsh_hook())
    options = ["--noprofile", "--norc"] if shell == "bash" else ["-d", "-f", "-i"]
    env = dict(os.environ, HOME=str(home), ZDOTDIR=str(home), PS1="", PS2="", TERM="dumb")
    env.pop("BASH_ENV", None)
    env.pop("ENV", None)
    return subprocess.run(
        [binary, *options], input=commands.replace("@HOOK@", shlex.quote(str(script))),
        cwd=home, env=env, text=True, capture_output=True, timeout=15,
    )


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_native_failure_capture_and_repeated_source(home, shell):
    failing_command = "sh -c 'printf \"original stderr\\n\" >&2; exit 7'"
    result = run_shell(home, shell, f""". @HOOK@
. @HOOK@
true
{failing_command}
printf 'status=%s\\n' "$?"
exit
""")
    assert result.returncode == 0, result.stderr
    assert "original stderr" in result.stderr
    assert "status=7" in result.stdout
    log = home / ".local/share/invoq/shell_failures.log"
    entries = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["command"] == failing_command
    assert entry["exit_code"] == 7
    assert Path(entry["cwd"]).resolve() == home.resolve()
    assert entry["stderr"] is None
    assert entry["stderr_file"] is None
    assert entry["stderr_captured"] is False
    assert log.stat().st_mode & 0o777 == 0o600


def test_bash_preserves_existing_traps_options_prompt_and_aliases(home):
    result = run_shell(home, "bash", r'''
set -- original argument
trap 'printf "old-err=%s:%s:%s:%s\n" "$?" "$BASH_COMMAND" "$1" "$2"' ERR
trap ':' DEBUG
PS1='my prompt> '
alias greeting='echo hello'
before_options=$(set +o)
before_debug=$(trap -p DEBUG)
. @HOOK@
. @HOOK@
false
printf 'status=%s\n' "$?"
printf 'prompt=%s\n' "$PS1"
alias greeting
test "$before_options" = "$(set +o)"
test "$before_debug" = "$(trap -p DEBUG)"
''')
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("old-err=1:false:original:argument") == 1
    assert "status=1" in result.stdout
    assert "prompt=my prompt> " in result.stdout
    assert "greeting='echo hello'" in result.stdout
    log = home / ".local/share/invoq/shell_failures.log"
    assert len(log.read_text().splitlines()) == 1


def test_bash_errexit_is_preserved(home):
    result = run_shell(home, "bash", ". @HOOK@\nset -e\nfalse\nprintf 'should not run'\n")
    assert result.returncode == 1
    assert "should not run" not in result.stdout
    entry = json.loads((home / ".local/share/invoq/shell_failures.log").read_text())
    assert entry["command"] == "false"


def test_zsh_appends_to_framework_hooks(home):
    result = run_shell(home, "zsh", r'''
framework_preexec() { print -r -- "framework-preexec:$1"; }
framework_precmd() { print -r -- "framework-precmd:$?"; }
preexec_functions=(framework_preexec)
precmd_functions=(framework_precmd)
. @HOOK@
. @HOOK@
false
print -r -- "preexec:${preexec_functions[*]}"
print -r -- "precmd:${precmd_functions[*]}"
exit
''')
    assert result.returncode == 0, result.stderr
    assert "framework-preexec:false" in result.stdout
    assert "framework-precmd:1" in result.stdout
    assert "preexec:framework_preexec _invoq_preexec" in result.stdout
    assert "precmd:framework_precmd _invoq_precmd" in result.stdout
    entries = (home / ".local/share/invoq/shell_failures.log").read_text().splitlines()
    assert len(entries) == 1
    assert json.loads(entries[0])["exit_code"] == 1


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_hook_keeps_stderr_attached_to_terminal(home, shell):
    if os.name == "nt" or shutil.which(shell) is None:
        pytest.skip(f"Native {shell} and POSIX terminals are required")
    import pty

    script = home / "hook.sh"
    script.write_text(bash_hook() if shell == "bash" else zsh_hook())
    options = ["--noprofile", "--norc"] if shell == "bash" else ["-d", "-f"]
    master, slave = pty.openpty()
    try:
        result = subprocess.run(
            [shutil.which(shell), *options, "-c", f". {shlex.quote(str(script))}; test -t 2"],
            cwd=home, env=dict(os.environ, HOME=str(home), ZDOTDIR=str(home)),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=slave, timeout=10,
        )
    finally:
        os.close(slave)
        os.close(master)
    assert result.returncode == 0


def test_bash_logging_failure_does_not_change_command_status(home):
    log = home / ".local/share/invoq/shell_failures.log"
    log.mkdir(parents=True)
    result = run_shell(home, "bash", ". @HOOK@\nfalse\nprintf 'status=%s\\n' \"$?\"\n")
    assert result.returncode == 0
    assert "status=1" in result.stdout
    assert "failed to save shell failure" in result.stderr


def test_bash_keeps_background_job_id(home):
    result = run_shell(home, "bash", r'''. @HOOK@
sleep 0.1 &
job=$!
false
test "$!" = "$job"
wait "$job"
''')
    assert result.returncode == 0, result.stderr
    assert len((home / ".local/share/invoq/shell_failures.log").read_text().splitlines()) == 1
