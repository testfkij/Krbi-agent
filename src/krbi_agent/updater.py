from __future__ import annotations

import os
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from . import __version__

GITHUB_RAW_UPDATE_URL = "https://raw.githubusercontent.com/testfkij/Krbi-agent/main/update.txt"
GITHUB_GIT_URL = "https://github.com/testfkij/Krbi-agent.git"
UPDATE_CACHE_TTL = 900


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    version: str
    version_type: str
    code: int


class UpdateError(RuntimeError):
    pass


def current_info() -> UpdateInfo:
    path = Path(__file__).resolve().parents[2] / "update.txt"
    if path.exists():
        try:
            return parse_update_text(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return UpdateInfo(__version__, "A1", 23628)


def parse_update_text(text: str) -> UpdateInfo:
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip().upper()] = value.strip()
    version = values.get("VERSION")
    version_type = values.get("VERSION_TYPE", "A1")
    code = values.get("CODE")
    if not version or code is None:
        raise UpdateError("update.txt is missing VERSION or CODE")
    return UpdateInfo(version, version_type, int(code))


def fetch_latest(url: str = GITHUB_RAW_UPDATE_URL, timeout: float = 4.0) -> UpdateInfo:
    request = Request(url, headers={"User-Agent": "KRBI-Agent-Updater/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return parse_update_text(response.read().decode("utf-8"))


def check_for_update(timeout: float = 1.5, force: bool = False) -> tuple[UpdateInfo, UpdateInfo | None]:
    local = current_info()
    cache = Path(os.getenv("KRBI_UPDATE_CACHE", Path.home() / ".cache" / "krbi-agent" / "update.json"))
    if not force and cache.exists():
        try:
            payload = json.loads(cache.read_text())
            if time.time() - float(payload.get("checked_at", 0)) < UPDATE_CACHE_TTL:
                remote = payload.get("remote")
                return local, (UpdateInfo(remote["version"], remote["version_type"], int(remote["code"])) if remote else None)
        except Exception:
            pass
    try:
        remote = fetch_latest(timeout=timeout)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"checked_at": time.time(), "remote": {"version":remote.version,"version_type":remote.version_type,"code":remote.code}}))
        return local, remote
    except Exception:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps({"checked_at": time.time(), "remote": None}))
        except Exception:
            pass
        return local, None


def _git_root() -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return Path(result.stdout.strip()) if result.stdout.strip() else None


def _run_update_git(root: Path) -> None:
    subprocess.run(["git", "fetch", "origin", "main", "--quiet"], cwd=root, check=True, timeout=60)
    local = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True, timeout=5).stdout.strip()
    remote = subprocess.run(["git", "rev-parse", "origin/main"], cwd=root, capture_output=True, text=True, check=True, timeout=5).stdout.strip()
    if local == remote:
        return
    subprocess.run(["git", "merge", "--ff-only", "origin/main"], cwd=root, check=True, timeout=60)


def reinstall_checkout() -> bool:
    root = _git_root()
    if root is None:
        print("KRBI reinstall unavailable: run from the GitHub checkout.")
        return False
    try:
        subprocess.run(["git", "fetch", "origin", "main", "--quiet"], cwd=root, check=True, timeout=60)
        subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=root, check=True, timeout=30)
        subprocess.run(["git", "clean", "-fd"], cwd=root, check=True, timeout=30)
    except Exception as exc:
        print(f"KRBI reinstall failed: {exc}")
        return False
    print("KRBI reinstall complete. Restarting…")
    os.execv(sys.executable, [sys.executable, "-m", "krbi_agent.cli", "run"])
    return True


def update_and_restart(argv: list[str]) -> bool:
    root = _git_root()
    if root is None:
        print("KRBI update unavailable: run from the GitHub checkout.")
        return False
    try:
        _run_update_git(root)
    except Exception as exc:
        print(f"KRBI update failed; continuing on the current version: {exc}")
        return False
    print("KRBI update applied. Restarting…")
    os.execv(sys.executable, [sys.executable, "-m", "krbi_agent.cli", *argv])
    return True
