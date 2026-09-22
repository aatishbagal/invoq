from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional, TextIO


@contextmanager
def _history_lock(file: TextIO) -> Iterator[None]:
    if os.name == "nt":
        import msvcrt

        file.seek(0)
        msvcrt.locking(file.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            file.seek(0)
            msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)


@dataclass
class HistoryEntry:
    command: str
    timestamp: str
    exit_code: int
    stderr: str
    cwd: str

    @classmethod
    def create(
        cls,
        command: str,
        exit_code: int,
        stderr: str,
        cwd: str,
    ) -> "HistoryEntry":
        return cls(
            command=command,
            timestamp=datetime.now().isoformat(),
            exit_code=exit_code,
            stderr=stderr[:500] if stderr else "",
            cwd=cwd,
        )

    @property
    def timestamp_dt(self) -> datetime:
        return datetime.fromisoformat(self.timestamp)

    @property
    def failed(self) -> bool:
        return self.exit_code != 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        return cls(**data)


def get_history_path() -> Path:
    data_dir = Path.home() / ".local" / "share" / "invoq"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "history.json"


class CommandHistory:
    def __init__(self, max_entries: int = 100):
        self.max_entries = max_entries
        self._history_path = get_history_path()

    def _load(self) -> List[HistoryEntry]:
        if not self._history_path.exists():
            return []

        try:
            with open(self._history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [HistoryEntry.from_dict(entry) for entry in data]
        except (json.JSONDecodeError, KeyError, TypeError, OSError):
            return []

    def _save(self, entries: List[HistoryEntry]) -> None:
        self._history_path.parent.mkdir(parents=True, exist_ok=True)

        serialized = json.dumps([entry.to_dict() for entry in entries], indent=2)
        with open(self._history_path, "a+", encoding="utf-8") as f, _history_lock(f):
            f.seek(0)
            f.truncate()
            f.write(serialized)
            f.flush()

    def add(
        self,
        command: str,
        exit_code: int,
        stderr: str,
        cwd: str,
    ) -> None:
        entries = self._load()

        new_entry = HistoryEntry.create(
            command=command,
            exit_code=exit_code,
            stderr=stderr,
            cwd=cwd,
        )

        entries.append(new_entry)

        if len(entries) > self.max_entries:
            entries = entries[-self.max_entries:]

        self._save(entries)

    def get_last(self) -> Optional[HistoryEntry]:
        entries = self._load()
        return entries[-1] if entries else None

    def get_last_failed(self) -> Optional[HistoryEntry]:
        entries = self._load()
        for entry in reversed(entries):
            if entry.failed:
                return entry
        return None

    def get_recent(self, n: int = 10) -> List[HistoryEntry]:
        entries = self._load()
        return entries[-n:] if entries else []

    def clear(self) -> None:
        self._save([])

    def search(self, query: str) -> List[HistoryEntry]:
        entries = self._load()
        q = query.lower()
        return [e for e in entries if q in e.command.lower()]
