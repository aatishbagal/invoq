from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import venv


WEB_URL = "https://github.com/aatishbagal/invoq"
REPOSITORY = f"{WEB_URL}.git"
API_URL = "https://api.github.com/repos/aatishbagal/invoq"
RECEIPT = "invoq-install.json"
BANNER = r"""  _
 (_)_ ____   _____   __ _
 | | '_ \ \ / / _ \ / _' |
 | | | | \ V / (_) | (_| |
 |_|_| |_|\_/ \___/ \__, |
                      | |
                      |_|"""


def github_json(endpoint: str) -> dict:
    request = Request(f"{API_URL}/{endpoint}", headers={
        "Accept": "application/vnd.github+json", "User-Agent": "invoq-installer",
    })
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read(2_000_001)
        if len(payload) > 2_000_000:
            raise ValueError("GitHub returned an oversized response.")
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("GitHub returned an invalid response.")
        return data
    except HTTPError as exc:
        if exc.code == 404 and endpoint == "releases/latest":
            raise ValueError("No stable release is available yet. Use the beta installer.") from exc
        raise ValueError(f"GitHub request failed (HTTP {exc.code}); try again later.") from exc
    except (URLError, TimeoutError) as exc:
        raise ValueError("Cannot reach GitHub; no update was installed.") from exc


def requirement(source: dict) -> str:
    if isinstance(source, dict) and source.get("kind") == "git":
        commit = source.get("commit")
        if isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit):
            return f"invoq @ git+{REPOSITORY}@{commit}"
    if isinstance(source, dict) and source.get("kind") == "wheel":
        url, digest = source.get("url"), source.get("sha256")
        pattern = re.escape(WEB_URL) + r"/releases/download/v(\d+\.\d+\.\d+)/invoq-\1-py3-none-any\.whl"
        if (isinstance(url, str) and re.fullmatch(pattern, url)
                and isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest)):
            return f"invoq @ {url}#sha256={digest}"
    raise ValueError("Invalid or untrusted installation source.")


def resolve_source(channel: str) -> dict:
    if channel == "beta":
        data = github_json("commits/main")
        source = {"kind": "git", "commit": data.get("sha") if isinstance(data, dict) else None}
    elif channel == "stable":
        data = github_json("releases/latest")
        tag = data.get("tag_name", "")
        if (data.get("draft") is not False or data.get("prerelease") is not False
                or not isinstance(tag, str) or not re.fullmatch(r"v\d+\.\d+\.\d+", tag)):
            raise ValueError("No supported stable release is available yet.")
        name = f"invoq-{tag[1:]}-py3-none-any.whl"
        assets = data.get("assets")
        if not isinstance(assets, list):
            raise ValueError("Stable release has no verified wheel available yet.")
        matches = [item for item in assets if isinstance(item, dict) and item.get("name") == name]
        if len(matches) != 1:
            raise ValueError("Stable release has no unique verified wheel available yet.")
        asset = matches[0]
        digest = asset.get("digest")
        if not isinstance(digest, str) or not digest.startswith("sha256:"):
            raise ValueError("Stable release wheel is missing its SHA-256 digest.")
        source = {"kind": "wheel", "url": asset.get("browser_download_url"), "sha256": digest[7:]}
        if source["url"] != f"{WEB_URL}/releases/download/{tag}/{name}":
            raise ValueError("Stable release wheel has an untrusted URL.")
    else:
        raise ValueError("Installation channel must be beta or stable.")
    requirement(source)
    return source


def install_directory(channel: str) -> Path:
    if channel not in ("beta", "stable"):
        raise ValueError("Installation channel must be beta or stable.")
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    elif system == "Linux":
        base = Path.home() / ".local" / "share"
    else:
        raise ValueError("The installer supports Linux, macOS, and Windows.")
    return base / "invoq" / channel


def environment_python(directory: Path) -> Path:
    return directory / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")


def read_receipt(directory: Path) -> dict:
    try:
        data = json.loads((directory / RECEIPT).read_text(encoding="utf-8"))
        if (not isinstance(data, dict) or data.get("channel") not in ("beta", "stable")
                or "source" not in data):
            raise ValueError("Invalid installation channel.")
        source = data.get("source")
        if source is not None:
            requirement(source)
            expected = "git" if data["channel"] == "beta" else "wheel"
            if source["kind"] != expected:
                raise ValueError("Installation channel does not match its source.")
        return data
    except (OSError, ValueError) as exc:
        raise ValueError("Not a managed invoq installation. Run this repository's installer first.") from exc


def write_receipt(directory: Path, channel: str, source: dict | None) -> None:
    path = directory / RECEIPT
    pending = path.with_suffix(".pending")
    pending.write_text(json.dumps({"channel": channel, "source": source}) + "\n", encoding="utf-8")
    pending.replace(path)


def verify_installation(python: Path, source: dict) -> str:
    requirement(source)
    script = """import json, sys
from importlib.metadata import distribution
package = distribution('invoq')
origin = json.loads(package.read_text('direct_url.json') or '{}')
source = json.loads(sys.argv[1])
if source['kind'] == 'git':
    valid = (origin.get('url') == sys.argv[2]
             and origin.get('vcs_info', {}).get('vcs') == 'git'
             and origin.get('vcs_info', {}).get('commit_id') == source['commit'])
else:
    valid = (origin.get('url') == source['url']
             and origin.get('archive_info', {}).get('hashes', {}).get('sha256') == source['sha256'])
if not valid:
    sys.exit('Installed package provenance does not match the requested source.')
print(package.version)
"""
    result = subprocess.run(
        [str(python), "-I", "-c", script, json.dumps(source), REPOSITORY],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def install_source(python: Path, source: dict) -> str:
    target = requirement(source)
    if source["kind"] == "git" and not shutil.which("git"):
        raise ValueError("Git is required for beta installation and updates.")
    print(f"Installing {target}", flush=True)
    subprocess.run(
        [str(python), "-I", "-m", "pip", "--isolated", "--require-virtualenv",
         "install", "--upgrade", "--force-reinstall", target],
        check=True,
    )
    return verify_installation(python, source)


def show_path_instructions(directory: Path) -> None:
    scripts = environment_python(directory).parent
    print("Add invoq to PATH in this terminal:")
    if platform.system() == "Windows":
        quoted = str(scripts).replace("'", "''")
        print(f"  $env:Path = '{quoted};' + $env:Path")
    else:
        print(f"  export PATH={shlex.quote(str(scripts))}:\"$PATH\"")
    print("Then run: invoq --version")
    print("Install Ollama yourself from https://ollama.com/download, then run: invoq setup")


def install(channel: str) -> None:
    directory = install_directory(channel)
    incomplete = True
    if directory.exists():
        receipt = read_receipt(directory)
        if receipt["channel"] != channel:
            raise ValueError("Existing installation belongs to another channel.")
        incomplete = receipt["source"] is None
    source = resolve_source(channel)
    if source["kind"] == "git" and not shutil.which("git"):
        raise ValueError("Install Git before running the beta installer.")
    python = environment_python(directory)
    if not directory.exists():
        directory.mkdir(parents=True)
        write_receipt(directory, channel, None)
    if incomplete or not python.is_file():
        venv.create(directory, with_pip=True)
    installed_version = install_source(python, source)
    write_receipt(directory, channel, source)
    print(f"Installed invoq {installed_version} ({channel}).")
    show_path_instructions(directory)


def managed_installation() -> tuple[Path, dict]:
    directory = Path(sys.prefix)
    if sys.prefix == sys.base_prefix:
        raise ValueError("Run this repository's installer to create a managed virtual environment first.")
    receipt = read_receipt(directory)
    if receipt["source"] is None:
        raise ValueError("Installation is incomplete; rerun the installer.")
    return directory, receipt


def update() -> None:
    directory, receipt = managed_installation()
    python = Path(sys.executable)
    verify_installation(python, receipt["source"])
    source = resolve_source(receipt["channel"])
    if source == receipt["source"]:
        print(f"invoq is already up to date on the {receipt['channel']} channel.")
        return
    installed_version = install_source(python, source)
    write_receipt(directory, receipt["channel"], source)
    print(f"Updated invoq to {installed_version} ({receipt['channel']}).")


def self_update() -> None:
    managed_installation()
    if platform.system() == "Windows":
        import psutil

        processes = [str(os.getpid())]
        try:
            parent = psutil.Process().parent()
            if parent is not None and parent.name().lower() == "invoq.exe":
                processes.append(str(parent.pid))
        except psutil.Error as exc:
            raise ValueError("Cannot identify the running launcher; use scripts/update.ps1.") from exc
        subprocess.Popen(
            [sys.executable, "-I", "-m", "invoq.lifecycle", "finish-update", *processes],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        print("Update opened in a separate window; it will report completion or failure there.")
    else:
        update()


def wait_for_process(pid: int) -> None:
    import ctypes
    from ctypes import wintypes

    if platform.system() != "Windows" or pid <= 0:
        raise ValueError("Launcher handoff requires a Windows process ID.")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x00100000, False, pid)
    if not handle:
        error = ctypes.get_last_error()
        if error == 87:
            return
        raise ctypes.WinError(error)
    try:
        if kernel.WaitForSingleObject(handle, 30_000) != 0:
            raise ValueError("The running launcher did not exit; update was not started.")
    finally:
        kernel.CloseHandle(handle)


def finish_update(process_ids: list[int]) -> None:
    for pid in process_ids:
        wait_for_process(pid)
    update()


def main() -> int:
    parser = argparse.ArgumentParser(description="Install or update invoq from its verified repository.")
    commands = parser.add_subparsers(dest="command", required=True)
    installer = commands.add_parser("install")
    installer.add_argument("channel", choices=("beta", "stable"), nargs="?", default="beta")
    updater = commands.add_parser("update")
    updater.add_argument("channel", choices=("beta", "stable"), nargs="?", default="beta")
    finisher = commands.add_parser("finish-update", help=argparse.SUPPRESS)
    finisher.add_argument("process_ids", type=int, nargs="+")
    commands.add_parser("apply-update", help=argparse.SUPPRESS)
    args = parser.parse_args()
    result = 0
    try:
        if args.command == "install":
            print(BANNER)
            print("invoq - Unstable beta" if args.channel == "beta" else "invoq - Stable release")
            install(args.channel)
        elif args.command == "update":
            python = environment_python(install_directory(args.channel))
            if not python.is_file():
                raise ValueError("Run the installer first; this channel is not installed.")
            subprocess.run([str(python), "-I", "-m", "invoq.lifecycle", "apply-update"], check=True)
        elif args.command == "finish-update":
            finish_update(args.process_ids)
        else:
            update()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"invoq installation/update failed: {exc}", file=sys.stderr)
        print("No success was recorded. If installation was interrupted, rerun the installer.", file=sys.stderr)
        result = 1
    if args.command == "finish-update":
        try:
            input("Press Enter to close this update window.")
        except EOFError:
            pass
    return result


if __name__ == "__main__":
    raise SystemExit(main())
