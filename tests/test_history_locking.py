import importlib
import json
import os
import sys
from types import SimpleNamespace

import pytest


pytestmark = pytest.mark.security


@pytest.fixture
def history(tmp_path, monkeypatch):
    module = importlib.import_module("invoq.core.history")
    monkeypatch.setattr(module, "get_history_path", lambda: tmp_path / "history.json")
    return module, module.CommandHistory()


@pytest.mark.parametrize("system", ["nt", "posix"])
def test_history_locks_before_replacing_and_flushes_before_unlock(history, monkeypatch, system):
    module, store = history
    path = store._history_path
    path.write_text("previous history", encoding="utf-8")
    calls = []

    def locking(fd, mode, count=None):
        calls.append(mode)
        if mode == 1:
            assert path.read_text(encoding="utf-8") == "previous history"
        else:
            assert json.loads(path.read_text(encoding="utf-8")) == []
        if system == "nt":
            assert os.lseek(fd, 0, os.SEEK_CUR) == 0
            assert count == 1

    monkeypatch.setattr(module, "os", SimpleNamespace(name=system), raising=False)
    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(locking=locking, LK_LOCK=1, LK_UNLCK=2))
    monkeypatch.setitem(sys.modules, "fcntl", SimpleNamespace(flock=locking, LOCK_EX=1, LOCK_UN=2))

    store._save([])

    assert calls == [1, 2]


@pytest.mark.parametrize("system", ["nt", "posix"])
def test_history_lock_failure_preserves_existing_file(history, monkeypatch, system):
    module, store = history
    path = store._history_path
    path.write_text("previous history", encoding="utf-8")

    def unavailable(*args):
        raise OSError("lock unavailable")

    monkeypatch.setattr(module, "os", SimpleNamespace(name=system), raising=False)
    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(locking=unavailable, LK_LOCK=1, LK_UNLCK=2))
    monkeypatch.setitem(sys.modules, "fcntl", SimpleNamespace(flock=unavailable, LOCK_EX=1, LOCK_UN=2))

    with pytest.raises(OSError, match="lock unavailable"):
        store._save([])
    assert path.read_text(encoding="utf-8") == "previous history"
