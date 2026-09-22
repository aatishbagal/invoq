import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest
from typer.testing import CliRunner


pytestmark = pytest.mark.security
ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
DIGEST = "b" * 64


@pytest.fixture
def lifecycle():
    return importlib.import_module("invoq.lifecycle")


def test_self_update_never_falls_back_to_pypi(monkeypatch):
    cli = importlib.import_module("invoq.main")
    run = Mock()
    monkeypatch.setattr(cli, "is_first_run", lambda: False)
    monkeypatch.setattr(cli.shutil, "which", lambda _: None)
    monkeypatch.setattr(cli.subprocess, "run", run)

    result = CliRunner().invoke(cli.app, ["self-update"])

    assert result.exit_code == 1
    run.assert_not_called()
    assert "installer" in result.output.lower()




@pytest.mark.parametrize("name", ["install.sh", "update.sh"])
def test_shell_scripts_do_not_install_by_pypi_name(name):
    text = (ROOT / "scripts" / name).read_text()
    assert "YOUR_USERNAME" not in text
    assert "pipx" not in text
    assert "install --user" not in text


@pytest.mark.parametrize("name", ["install.ps1", "update.ps1"])
def test_native_windows_scripts_exist(name):
    text = (ROOT / "scripts" / name).read_text()
    assert "$PSScriptRoot" in text
    assert "$LASTEXITCODE" in text
    assert "ExecutionPolicy Bypass" not in text


def test_beta_resolves_main_to_immutable_commit(lifecycle, monkeypatch):
    api = Mock(return_value={"sha": SHA})
    monkeypatch.setattr(lifecycle, "github_json", api)

    source = lifecycle.resolve_source("beta")

    api.assert_called_once_with("commits/main")
    assert source == {"kind": "git", "commit": SHA}
    assert lifecycle.requirement(source) == f"invoq @ git+{lifecycle.REPOSITORY}@{SHA}"


@pytest.mark.parametrize("response", [{}, {"sha": "dev"}, {"sha": "a" * 39}, []])
def test_invalid_beta_revision_fails_closed(lifecycle, monkeypatch, response):
    monkeypatch.setattr(lifecycle, "github_json", lambda _: response)
    with pytest.raises(ValueError):
        lifecycle.resolve_source("beta")


@pytest.fixture
def release(lifecycle):
    tag = "v1.2.3"
    name = "invoq-1.2.3-py3-none-any.whl"
    return {
        "tag_name": tag, "draft": False, "prerelease": False,
        "assets": [{"name": name, "digest": f"sha256:{DIGEST}",
                    "browser_download_url": f"{lifecycle.WEB_URL}/releases/download/{tag}/{name}"}],
    }


def test_stable_uses_release_wheel_and_checksum(lifecycle, release, monkeypatch):
    api = Mock(return_value=release)
    monkeypatch.setattr(lifecycle, "github_json", api)
    source = lifecycle.resolve_source("stable")
    api.assert_called_once_with("releases/latest")
    assert source["kind"] == "wheel"
    assert lifecycle.requirement(source).endswith(f"#sha256={DIGEST}")
    assert "/releases/download/v1.2.3/" in lifecycle.requirement(source)


@pytest.mark.parametrize("field,value", [
    ("draft", True), ("prerelease", True), ("tag_name", "dev"), ("assets", []),
])
def test_unpublished_or_incomplete_stable_release_is_rejected(lifecycle, release, monkeypatch, field, value):
    release[field] = value
    monkeypatch.setattr(lifecycle, "github_json", lambda _: release)
    with pytest.raises(ValueError):
        lifecycle.resolve_source("stable")


@pytest.mark.parametrize("field,value", [
    ("browser_download_url", "https://example.com/invoq.whl"),
    ("digest", None), ("digest", "sha256:bad"),
])
def test_stable_rejects_untrusted_asset(lifecycle, release, monkeypatch, field, value):
    release["assets"][0][field] = value
    monkeypatch.setattr(lifecycle, "github_json", lambda _: release)
    with pytest.raises(ValueError):
        lifecycle.resolve_source("stable")


@pytest.mark.parametrize("system,parts", [
    ("Linux", (".local", "share", "invoq", "beta")),
    ("Darwin", ("Library", "Application Support", "invoq", "beta")),
    ("Windows", ("AppData", "Local", "invoq", "beta")),
])
def test_native_install_paths(lifecycle, monkeypatch, tmp_path, system, parts):
    monkeypatch.setattr(lifecycle.platform, "system", lambda: system)
    monkeypatch.setattr(lifecycle.Path, "home", lambda: tmp_path)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    assert lifecycle.install_directory("beta") == tmp_path.joinpath(*parts)
    expected = ("Scripts", "python.exe") if system == "Windows" else ("bin", "python")
    assert lifecycle.environment_python(tmp_path) == tmp_path.joinpath(*expected)


def test_install_uses_pinned_source_and_own_interpreter(lifecycle, monkeypatch, tmp_path):
    env = tmp_path / "install with spaces"
    source = {"kind": "git", "commit": SHA}
    monkeypatch.setattr(lifecycle, "resolve_source", lambda _: source)
    monkeypatch.setattr(lifecycle, "install_directory", lambda _: env)
    monkeypatch.setattr(lifecycle.shutil, "which", lambda _: "/usr/bin/git")
    create = Mock()
    monkeypatch.setattr(lifecycle.venv, "create", create)
    install = Mock()
    monkeypatch.setattr(lifecycle, "install_source", install)

    lifecycle.install("beta")

    create.assert_called_once_with(env, with_pip=True)
    install.assert_called_once_with(lifecycle.environment_python(env), source)
    assert lifecycle.read_receipt(env) == {"channel": "beta", "source": source}


def test_existing_unmanaged_directory_is_not_overwritten(lifecycle, monkeypatch, tmp_path):
    monkeypatch.setattr(lifecycle, "install_directory", lambda _: tmp_path)
    install = Mock()
    monkeypatch.setattr(lifecycle, "install_source", install)
    with pytest.raises(ValueError, match="managed"):
        lifecycle.install("beta")
    install.assert_not_called()


def test_failed_install_does_not_record_success(lifecycle, monkeypatch, tmp_path):
    env = tmp_path / "beta"
    monkeypatch.setattr(lifecycle, "resolve_source", lambda _: {"kind": "git", "commit": SHA})
    monkeypatch.setattr(lifecycle, "install_directory", lambda _: env)
    monkeypatch.setattr(lifecycle.shutil, "which", lambda _: "/usr/bin/git")
    monkeypatch.setattr(lifecycle.venv, "create", Mock())
    monkeypatch.setattr(lifecycle, "install_source", Mock(side_effect=OSError("failed")))
    with pytest.raises(OSError):
        lifecycle.install("beta")
    assert lifecycle.read_receipt(env)["source"] is None


def test_interrupted_environment_creation_can_be_retried(lifecycle, monkeypatch, tmp_path):
    lifecycle.write_receipt(tmp_path, "beta", None)
    python = lifecycle.environment_python(tmp_path)
    python.parent.mkdir()
    python.write_text("partial environment")
    monkeypatch.setattr(lifecycle, "install_directory", lambda _: tmp_path)
    monkeypatch.setattr(lifecycle, "resolve_source", lambda _: {"kind": "git", "commit": SHA})
    monkeypatch.setattr(lifecycle.shutil, "which", lambda _: "/usr/bin/git")
    create = Mock()
    monkeypatch.setattr(lifecycle.venv, "create", create)
    monkeypatch.setattr(lifecycle, "install_source", Mock())

    lifecycle.install("beta")

    create.assert_called_once_with(tmp_path, with_pip=True)
    assert lifecycle.read_receipt(tmp_path)["source"]["commit"] == SHA


def test_update_stays_on_recorded_channel(lifecycle, monkeypatch, tmp_path):
    previous = {"kind": "git", "commit": "c" * 40}
    current = {"kind": "git", "commit": SHA}
    lifecycle.write_receipt(tmp_path, "beta", previous)
    monkeypatch.setattr(lifecycle.sys, "prefix", str(tmp_path))
    monkeypatch.setattr(lifecycle.sys, "base_prefix", str(tmp_path / "base"))
    monkeypatch.setattr(lifecycle, "verify_installation", Mock())
    resolve = Mock(return_value=current)
    monkeypatch.setattr(lifecycle, "resolve_source", resolve)
    install = Mock()
    monkeypatch.setattr(lifecycle, "install_source", install)

    lifecycle.update()

    resolve.assert_called_once_with("beta")
    install.assert_called_once_with(Path(lifecycle.sys.executable), current)
    assert lifecycle.read_receipt(tmp_path)["source"] == current


def test_update_failure_preserves_receipt(lifecycle, monkeypatch, tmp_path):
    previous = {"kind": "git", "commit": "c" * 40}
    lifecycle.write_receipt(tmp_path, "beta", previous)
    monkeypatch.setattr(lifecycle.sys, "prefix", str(tmp_path))
    monkeypatch.setattr(lifecycle.sys, "base_prefix", str(tmp_path / "base"))
    monkeypatch.setattr(lifecycle, "verify_installation", Mock())
    monkeypatch.setattr(lifecycle, "resolve_source", lambda _: {"kind": "git", "commit": SHA})
    monkeypatch.setattr(lifecycle, "install_source", Mock(side_effect=OSError("failed")))
    with pytest.raises(OSError):
        lifecycle.update()
    assert lifecycle.read_receipt(tmp_path)["source"] == previous


def test_pip_receives_only_pinned_requirement(lifecycle, monkeypatch, tmp_path):
    python = tmp_path / "python"
    source = {"kind": "git", "commit": SHA}
    monkeypatch.setattr(lifecycle.shutil, "which", lambda _: "/usr/bin/git")
    run = Mock()
    monkeypatch.setattr(lifecycle.subprocess, "run", run)
    monkeypatch.setattr(lifecycle, "verify_installation", Mock())

    lifecycle.install_source(python, source)

    command = run.call_args_list[0].args[0]
    assert command[:7] == [str(python), "-I", "-m", "pip", "--isolated", "--require-virtualenv", "install"]
    assert command[-1] == lifecycle.requirement(source)
    assert "--user" not in command
    assert run.call_args_list[0].kwargs["check"] is True


@pytest.mark.parametrize("system", ["Linux", "Darwin", "Windows"])
def test_ollama_instructions_do_not_require_linux_shell(monkeypatch, system):
    manager = importlib.import_module("invoq.llm.ollama_manager")
    monkeypatch.setattr("platform.system", lambda: system)
    instructions = manager.get_install_instructions()
    assert "https://ollama.com/download" in instructions
    assert "| sh" not in instructions


def test_setup_status_does_not_print_linux_only_installer():
    wizard = importlib.import_module("invoq.ui.setup_wizard")
    manager = importlib.import_module("invoq.llm.ollama_manager")
    with wizard.console.capture() as capture:
        wizard.display_ollama_status(manager.OllamaInfo(manager.OllamaStatus.NOT_INSTALLED, None, "", ""))
    assert "| sh" not in capture.get()


def test_no_stable_release_fails_before_environment_creation(lifecycle, monkeypatch):
    request = Mock(side_effect=HTTPError("https://api.github.com", 404, "Not Found", {}, None))
    monkeypatch.setattr(lifecycle, "urlopen", request)
    create = Mock()
    monkeypatch.setattr(lifecycle.venv, "create", create)
    with pytest.raises(ValueError, match="No stable release"):
        lifecycle.resolve_source("stable")
    create.assert_not_called()


@pytest.mark.parametrize("error", [URLError("offline"), TimeoutError()])
def test_network_failure_has_no_package_fallback(lifecycle, monkeypatch, error):
    monkeypatch.setattr(lifecycle, "urlopen", Mock(side_effect=error))
    install = Mock()
    monkeypatch.setattr(lifecycle, "install_source", install)
    with pytest.raises(ValueError, match="Cannot reach GitHub"):
        lifecycle.resolve_source("beta")
    install.assert_not_called()


@pytest.mark.parametrize("channel,source", [
    ("beta", {"kind": "git", "commit": SHA}),
    ("stable", {"kind": "wheel", "url": "https://github.com/aatishbagal/invoq/releases/download/v1.2.3/invoq-1.2.3-py3-none-any.whl", "sha256": DIGEST}),
])
def test_current_installation_is_not_reinstalled(lifecycle, monkeypatch, tmp_path, channel, source):
    lifecycle.write_receipt(tmp_path, channel, source)
    monkeypatch.setattr(lifecycle.sys, "prefix", str(tmp_path))
    monkeypatch.setattr(lifecycle.sys, "base_prefix", str(tmp_path / "base"))
    monkeypatch.setattr(lifecycle, "verify_installation", Mock())
    resolve = Mock(return_value=source)
    monkeypatch.setattr(lifecycle, "resolve_source", resolve)
    install = Mock()
    monkeypatch.setattr(lifecycle, "install_source", install)

    lifecycle.update()

    resolve.assert_called_once_with(channel)
    install.assert_not_called()


@pytest.mark.parametrize("data", [
    [], {}, {"channel": "beta"}, {"channel": "other", "source": None},
    {"channel": "stable", "source": {"kind": "git", "commit": SHA}},
    {"channel": "beta", "source": {"kind": "git", "commit": "main"}},
])
def test_invalid_install_receipt_fails_closed(lifecycle, tmp_path, data):
    (tmp_path / lifecycle.RECEIPT).write_text(json.dumps(data))
    with pytest.raises(ValueError, match="managed"):
        lifecycle.read_receipt(tmp_path)


@pytest.mark.parametrize("kind", ["git", "wheel"])
@pytest.mark.parametrize("matches", [False, True])
def test_installed_provenance_is_verified(lifecycle, monkeypatch, kind, matches):
    source = {"kind": "git", "commit": SHA} if kind == "git" else {
        "kind": "wheel", "url": f"{lifecycle.WEB_URL}/releases/download/v1.2.3/invoq-1.2.3-py3-none-any.whl",
        "sha256": DIGEST,
    }
    origin = {"url": lifecycle.REPOSITORY, "vcs_info": {"vcs": "git", "commit_id": SHA}}
    if kind == "wheel":
        origin = {"url": source["url"], "archive_info": {"hashes": {"sha256": DIGEST}}}
    if not matches:
        origin["url"] = "https://example.com/unrelated"
    monkeypatch.setattr("importlib.metadata.distribution", lambda _: SimpleNamespace(
        read_text=lambda _: json.dumps(origin), version="test-version",
    ))

    def run(command, **kwargs):
        with monkeypatch.context() as context:
            context.setattr(sys, "argv", ["-c", *command[4:]])
            exec(command[3], {})
        return SimpleNamespace(stdout="test-version\n")

    monkeypatch.setattr(lifecycle.subprocess, "run", run)
    if matches:
        assert lifecycle.verify_installation(Path(sys.executable), source) == "test-version"
    else:
        with pytest.raises(SystemExit, match="provenance"):
            lifecycle.verify_installation(Path(sys.executable), source)


def test_windows_self_update_hands_off_before_modifying_packages(lifecycle, monkeypatch):
    parent = SimpleNamespace(pid=123, name=lambda: "invoq.exe")
    monkeypatch.setattr(lifecycle, "managed_installation", Mock())
    monkeypatch.setattr(lifecycle.platform, "system", lambda: "Windows")
    monkeypatch.setattr("psutil.Process", lambda: SimpleNamespace(parent=lambda: parent))
    monkeypatch.setattr(lifecycle.subprocess, "CREATE_NEW_CONSOLE", 16, raising=False)
    launch = Mock()
    monkeypatch.setattr(lifecycle.subprocess, "Popen", launch)
    update = Mock()
    monkeypatch.setattr(lifecycle, "update", update)

    lifecycle.self_update()

    command = launch.call_args.args[0]
    assert command[:5] == [sys.executable, "-I", "-m", "invoq.lifecycle", "finish-update"]
    assert str(lifecycle.os.getpid()) in command and "123" in command
    assert launch.call_args.kwargs == {"creationflags": 16}
    update.assert_not_called()


@pytest.mark.parametrize("exited", [False, True])
def test_windows_update_waits_for_launcher(lifecycle, monkeypatch, exited):
    wait = Mock(side_effect=None if exited else ValueError("still running"))
    monkeypatch.setattr(lifecycle, "wait_for_process", wait)
    update = Mock()
    monkeypatch.setattr(lifecycle, "update", update)
    if exited:
        lifecycle.finish_update([123, 456])
        assert wait.call_count == 2
        update.assert_called_once_with()
    else:
        with pytest.raises(ValueError):
            lifecycle.finish_update([123, 456])
        update.assert_not_called()


@pytest.mark.skipif(sys.platform == "win32", reason="Bash installer targets Linux and macOS")
@pytest.mark.parametrize("script", ["install.sh", "update.sh"])
def test_bash_wrappers_can_show_help_from_another_directory(script, tmp_path):
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / script), "--help"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "beta" in result.stdout and "stable" in result.stdout


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="PowerShell is checked on native CI")
def test_powershell_scripts_parse(tmp_path):
    script = """$ErrorActionPreference = 'Stop'
foreach ($file in $args) {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($file, [ref]$tokens, [ref]$parseErrors) | Out-Null
    if ($parseErrors.Count -gt 0) { throw ($parseErrors | Out-String) }
}
"""
    checker = tmp_path / "check scripts.ps1"
    checker.write_text(script)
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(checker),
         *[str(ROOT / "scripts" / name) for name in ("install.ps1", "update.ps1", "bootstrap.ps1")]],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr




@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows wrapper check")
@pytest.mark.parametrize("script", ["install.ps1", "update.ps1"])
def test_windows_wrappers_can_show_help(script, tmp_path):
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(ROOT / "scripts" / script), "-Help"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "beta" in result.stdout and "stable" in result.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows process handle check")
def test_windows_waits_for_real_process_exit(lifecycle):
    process = subprocess.Popen([sys.executable, "-I", "-c", "import time; time.sleep(0.2)"])
    lifecycle.wait_for_process(process.pid)
    assert process.wait(timeout=2) == 0




@pytest.mark.skipif(sys.platform == "win32", reason="Bash installer targets Linux and macOS")
@pytest.mark.parametrize("download_succeeds", [True, False])
def test_piped_installer_works_without_a_checkout(tmp_path, monkeypatch, download_succeeds):
    import os

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    curl = fake_bin / "curl"
    log = tmp_path / "download-url.txt"
    curl.write_text(
        f"#!{sys.executable}\n"
        "import pathlib, sys\n"
        f"pathlib.Path({str(log)!r}).write_text(sys.argv[-1])\n"
        f"sys.exit(22) if not {download_succeeds!r} else None\n"
        "output = pathlib.Path(sys.argv[sys.argv.index('--output') + 1])\n"
        f"output.write_bytes(pathlib.Path({str(ROOT / 'src/invoq/lifecycle.py')!r}).read_bytes())\n"
    )
    curl.chmod(0o755)
    monkeypatch.setenv("PATH", str(fake_bin) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("TMPDIR", str(tmp_path))

    result = subprocess.run(
        ["bash", "-s", "--", "--help"], cwd=tmp_path,
        input=(ROOT / "scripts/install.sh").read_text(), capture_output=True, text=True,
    )

    assert log.read_text() == "https://raw.githubusercontent.com/aatishbagal/invoq/main/src/invoq/lifecycle.py"
    if download_succeeds:
        assert result.returncode == 0, result.stderr
        assert "beta" in result.stdout and "stable" in result.stdout
    else:
        assert result.returncode != 0
        assert "usage:" not in result.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="Native PowerShell direct installer check")
@pytest.mark.parametrize("download_succeeds", [True, False])
def test_powershell_direct_installer_works_without_checkout(tmp_path, download_succeeds):
    def quoted(path):
        return "'" + str(path).replace("'", "''") + "'"

    log = tmp_path / "download-url.txt"
    harness = tmp_path / "direct installer.ps1"
    harness.write_text(f"""$ErrorActionPreference = 'Stop'
function Get-Command {{
    param($Name, $CommandType, $ErrorAction)
    if ($Name -eq 'python3') {{ [pscustomobject]@{{ Source = {quoted(sys.executable)} }} }}
}}
function Invoke-WebRequest {{
    param([switch]$UseBasicParsing, $ErrorAction, $Uri, $OutFile)
    [IO.File]::WriteAllText({quoted(log)}, $Uri)
    if (${str(not download_succeeds).lower()}) {{ throw 'download failed' }}
    [IO.File]::WriteAllText($OutFile, "print('remote-helper-ran')")
}}
& ([scriptblock]::Create([IO.File]::ReadAllText({quoted(ROOT / 'scripts/install.ps1')}))) -Help
""")
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(harness)],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert log.read_text() == "https://raw.githubusercontent.com/aatishbagal/invoq/main/src/invoq/lifecycle.py"
    if download_succeeds:
        assert result.returncode == 0, result.stderr
        assert "remote-helper-ran" in result.stdout
    else:
        assert result.returncode != 0
        assert "remote-helper-ran" not in result.stdout
