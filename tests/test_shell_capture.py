from datetime import datetime
import json
import os
from pathlib import Path
import stat

import pytest

from invoq.shell.capture import record_failure


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.mark.skipif(os.name == "nt", reason="Linux shell capture uses POSIX file locking")
def test_failure_record_is_private_valid_json_and_preserves_values(home):
    command = 'printf "quoted"\nfalse \\path\t\x1b'
    cwd = '/some/"quoted"/directory\n'
    previous_umask = os.umask(0)
    try:
        record_failure(command, 7, cwd)
    finally:
        os.umask(previous_umask)

    log = home / ".local/share/invoq/shell_failures.log"
    assert stat.S_IMODE(log.stat().st_mode) == 0o600
    lines = log.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert set(entry) == {"command", "exit_code", "stderr", "stderr_file", "stderr_captured", "cwd", "timestamp"}
    assert entry["command"] == command
    assert entry["exit_code"] == 7
    assert entry["cwd"] == cwd
    assert entry["stderr_file"] is None
    assert entry["stderr"] is None
    assert entry["stderr_captured"] is False
    assert datetime.fromisoformat(entry["timestamp"]).tzinfo is not None
    assert list(home.iterdir()) == [home / ".local"]


@pytest.mark.skipif(os.name == "nt", reason="Linux shell capture uses POSIX file locking")
def test_appends_records_and_tightens_existing_log_permissions(home):
    record_failure("first", 1, str(home))
    log = home / ".local/share/invoq/shell_failures.log"
    log.chmod(0o644)
    record_failure("second", 2, str(home))
    assert [json.loads(line)["command"] for line in log.read_text().splitlines()] == ["first", "second"]
    assert stat.S_IMODE(log.stat().st_mode) == 0o600


@pytest.mark.skipif(os.name == "nt", reason="Linux shell capture uses POSIX file locking")
def test_refuses_symlink_log(home):
    target = home / "unrelated"
    target.write_text("keep me")
    log = home / ".local/share/invoq/shell_failures.log"
    log.parent.mkdir(parents=True)
    log.symlink_to(target)
    with pytest.raises(OSError):
        record_failure("false", 1, str(home))
    assert target.read_text() == "keep me"


def test_success_does_not_create_log(home):
    record_failure("true", 0, str(home))
    assert list(home.iterdir()) == []
