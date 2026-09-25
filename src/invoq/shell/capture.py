from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import sys


def record_failure(command: str, exit_code: int, cwd: str) -> None:
    if exit_code == 0:
        return
    import fcntl

    directory = Path.home() / ".local/share/invoq"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
    descriptor = os.open(directory / "shell_failures.log", flags, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as log:
        info = os.fstat(log.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise OSError("Failure log must be a regular file owned by the current user.")
        os.fchmod(log.fileno(), 0o600)
        # Future debug may offer an approved SafeExecutor rerun using subprocess.PIPE
        # to capture fresh stderr without changing this shell's terminal streams.
        entry = {
            "command": command,
            "exit_code": exit_code,
            "stderr": None,
            "stderr_file": None,
            "stderr_captured": False,
            "cwd": cwd,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        fcntl.flock(log.fileno(), fcntl.LOCK_EX)
        try:
            log.write(json.dumps(entry, ensure_ascii=True) + "\n")
            log.flush()
        finally:
            fcntl.flock(log.fileno(), fcntl.LOCK_UN)


def main() -> int:
    try:
        if len(sys.argv) == 5 and sys.argv[1] == "record":
            record_failure(sys.argv[2], int(sys.argv[3]), sys.argv[4])
        else:
            return 2
    except (OSError, ValueError) as exc:
        print(f"invoq shell capture: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
