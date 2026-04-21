from __future__ import annotations

import pytest

from invoq.core.history import CommandHistory, HistoryEntry


@pytest.fixture
def temp_history(tmp_path, monkeypatch) -> CommandHistory:
    monkeypatch.setattr(
        "invoq.core.history.get_history_path",
        lambda: tmp_path / "history.json",
    )
    return CommandHistory(max_entries=100)


class TestCommandHistory:
    def test_add_entry(self, temp_history: CommandHistory) -> None:
        temp_history.add("ls -la", 0, "", "/home/user")

        recent = temp_history.get_recent()
        assert len(recent) == 1
        assert recent[0].command == "ls -la"
        assert recent[0].exit_code == 0
        assert recent[0].cwd == "/home/user"

    def test_get_last(self, temp_history: CommandHistory) -> None:
        temp_history.add("echo one", 0, "", "/tmp")
        temp_history.add("echo two", 0, "", "/tmp")
        temp_history.add("echo three", 0, "", "/tmp")

        last = temp_history.get_last()
        assert last is not None
        assert last.command == "echo three"

    def test_get_last_failed(self, temp_history: CommandHistory) -> None:
        temp_history.add("ls", 0, "", "/tmp")
        temp_history.add("cat /nope", 1, "No such file", "/tmp")
        temp_history.add("echo ok", 0, "", "/tmp")
        temp_history.add("false", 1, "", "/tmp")
        temp_history.add("true", 0, "", "/tmp")

        last_failed = temp_history.get_last_failed()
        assert last_failed is not None
        assert last_failed.command == "false"
        assert last_failed.failed is True

    def test_get_last_failed_none_when_all_succeed(
        self, temp_history: CommandHistory
    ) -> None:
        temp_history.add("ls", 0, "", "/tmp")
        temp_history.add("echo hi", 0, "", "/tmp")

        assert temp_history.get_last_failed() is None

    def test_max_entries(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(
            "invoq.core.history.get_history_path",
            lambda: tmp_path / "history.json",
        )
        history = CommandHistory(max_entries=5)

        for i in range(10):
            history.add(f"cmd {i}", 0, "", "/tmp")

        recent = history.get_recent(100)
        assert len(recent) == 5
        # Should keep the most recent 5 (cmd 5 through cmd 9)
        assert recent[0].command == "cmd 5"
        assert recent[-1].command == "cmd 9"

    def test_clear(self, temp_history: CommandHistory) -> None:
        temp_history.add("ls", 0, "", "/tmp")
        temp_history.add("pwd", 0, "", "/tmp")
        assert temp_history.get_last() is not None

        temp_history.clear()

        assert temp_history.get_recent() == []
        assert temp_history.get_last() is None

    def test_search(self, temp_history: CommandHistory) -> None:
        temp_history.add("git status", 0, "", "/repo")
        temp_history.add("ls -la", 0, "", "/repo")
        temp_history.add("git log", 0, "", "/repo")
        temp_history.add("cat README.md", 0, "", "/repo")

        results = temp_history.search("git")
        assert len(results) == 2
        assert all("git" in e.command for e in results)

        # case-insensitive
        upper_results = temp_history.search("GIT")
        assert len(upper_results) == 2

        # no matches
        assert temp_history.search("nonexistent") == []

    def test_empty_history(self, temp_history: CommandHistory) -> None:
        assert temp_history.get_last() is None
        assert temp_history.get_last_failed() is None
        assert temp_history.get_recent() == []
        assert temp_history.search("anything") == []

    def test_corrupted_file_handled(
        self, tmp_path, monkeypatch
    ) -> None:
        history_path = tmp_path / "history.json"
        monkeypatch.setattr(
            "invoq.core.history.get_history_path",
            lambda: history_path,
        )
        # Write invalid JSON
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text("{ not valid json !!!")

        history = CommandHistory()

        # Should not crash
        assert history.get_recent() == []
        assert history.get_last() is None

        # Should be able to recover by adding new entries
        history.add("recovered", 0, "", "/tmp")
        assert history.get_last().command == "recovered"

    def test_stderr_truncated_to_500(self, temp_history: CommandHistory) -> None:
        long_err = "x" * 1000
        temp_history.add("failing", 1, long_err, "/tmp")

        last = temp_history.get_last()
        assert last is not None
        assert len(last.stderr) == 500

    def test_history_entry_roundtrip(self) -> None:
        entry = HistoryEntry.create("ls", 0, "", "/tmp")
        data = entry.to_dict()
        restored = HistoryEntry.from_dict(data)

        assert restored.command == entry.command
        assert restored.exit_code == entry.exit_code
        assert restored.cwd == entry.cwd
        assert restored.timestamp == entry.timestamp

    def test_failed_property(self) -> None:
        ok = HistoryEntry.create("ls", 0, "", "/tmp")
        bad = HistoryEntry.create("false", 1, "", "/tmp")

        assert ok.failed is False
        assert bad.failed is True
