from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import time
from uuid import uuid4


SOURCE_LINE = (
    '[ -r "$HOME/.config/invoq/shell_hook.sh" ] && '
    '. "$HOME/.config/invoq/shell_hook.sh" # invoq shell hook'
)
RC_NAMES = {"bash": ".bashrc", "zsh": ".zshrc"}


@dataclass(frozen=True)
class HookInstallation:
    shell: str
    script: Path
    rc: Path


@dataclass(frozen=True)
class HookStatus:
    script: Path
    script_exists: bool
    sourced_from: tuple[Path, ...]
    log: Path
    log_exists: bool
    log_recent: bool


def installation_plan() -> HookInstallation:
    shell = Path(os.environ.get("SHELL", "")).name
    if shell not in RC_NAMES:
        raise ValueError("Shell hooks support bash and zsh. Set SHELL to your shell executable.")
    home = Path.home()
    script = home / ".config/invoq/shell_hook.sh"
    if script.is_file():
        for other, rc_name in RC_NAMES.items():
            if other != shell and _has_source(home / rc_name):
                raise ValueError(
                    f"Hooks are already configured for {other}. "
                    "Run 'invoq shell uninstall' before switching shells."
                )
    return HookInstallation(
        shell=shell,
        script=script,
        rc=home / RC_NAMES[shell],
    )


def _has_source(path: Path) -> bool:
    return path.is_file() and any(
        line.strip() == SOURCE_LINE for line in path.read_text().splitlines()
    )


def install_shell_hooks() -> None:
    plan = installation_plan()
    from invoq.shell.hooks import bash_hook, zsh_hook

    content = bash_hook() if plan.shell == "bash" else zsh_hook()
    previous = plan.rc.read_text() if plan.rc.exists() else ""
    plan.script.parent.mkdir(parents=True, exist_ok=True)
    plan.script.write_text(content)
    if not _has_source(plan.rc):
        separator = "\n" if previous and not previous.endswith("\n") else ""
        with plan.rc.open("a") as rc:
            rc.write(separator + SOURCE_LINE + "\n")
    print(f"Installed {plan.shell} hooks in {plan.script}.")
    print(f"Restart your shell or source {plan.rc} to activate capture.")


def uninstall_shell_hooks() -> None:
    home = Path.home()
    for name in RC_NAMES.values():
        rc = home / name
        if _has_source(rc):
            lines = rc.read_text().splitlines(keepends=True)
            rc.write_text("".join(line for line in lines if line.strip() != SOURCE_LINE))
    script = home / ".config/invoq/shell_hook.sh"
    if script.exists():
        archive = script.parent / "deprecated"
        archive.mkdir(exist_ok=True)
        destination = archive / f"shell_hook-{uuid4().hex}.sh"
        script.rename(destination)
        print(f"Archived the hook script at {destination}.")
    print("Shell hooks uninstalled. Captured history has been preserved.")
    print("Restart existing shells to stop their active hooks.")


def get_shell_status() -> HookStatus:
    home = Path.home()
    script = home / ".config/invoq/shell_hook.sh"
    log = home / ".local/share/invoq/shell_failures.log"
    log_exists = log.is_file()
    recent = False
    if log_exists:
        stat = log.stat()
        recent = stat.st_size > 0 and 0 <= time.time() - stat.st_mtime <= 86400
    return HookStatus(
        script=script,
        script_exists=script.is_file(),
        sourced_from=tuple(home / name for name in RC_NAMES.values() if _has_source(home / name)),
        log=log,
        log_exists=log_exists,
        log_recent=recent,
    )
