from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from . import __version__

GITHUB_RAW_UPDATE_URL = "https://raw.githubusercontent.com/testfkij/Krbi-agent/main/update.txt"
GITHUB_RAW_VERSIONS_URL = "https://raw.githubusercontent.com/testfkij/Krbi-agent/main/versions.json"
GITHUB_GIT_URL = "https://github.com/testfkij/Krbi-agent.git"
GITHUB_ARCHIVE_URL = "https://codeload.github.com/testfkij/Krbi-agent/zip/{commit}"
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


def _get_json(url: str, timeout: float = 5.0):
    request = Request(url, headers={"User-Agent": "KRBI-Agent-Updater/1.1"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_latest(url: str = GITHUB_RAW_UPDATE_URL, timeout: float = 4.0) -> UpdateInfo:
    request = Request(url, headers={"User-Agent": "KRBI-Agent-Updater/1.1"})
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
        cache.write_text(json.dumps({"checked_at": time.time(), "remote": {"version": remote.version, "version_type": remote.version_type, "code": remote.code}}))
        return local, remote
    except Exception:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps({"checked_at": time.time(), "remote": None}))
        except Exception:
            pass
        return local, None


def fetch_versions(timeout: float = 5.0) -> list[dict]:
    data = _get_json(GITHUB_RAW_VERSIONS_URL, timeout)
    versions = data.get("versions", [])
    if not isinstance(versions, list):
        raise UpdateError("invalid versions.json")
    return [v for v in versions if isinstance(v, dict) and v.get("version") and v.get("commit")]


def available_versions(timeout: float = 5.0) -> list[dict]:
    versions = fetch_versions(timeout)
    local = current_info()
    current = {"version": local.version, "version_type": local.version_type, "code": local.code, "commit": None, "current": True}
    if not any(v.get("version") == local.version for v in versions):
        versions.insert(0, current)
    for item in versions:
        item.setdefault("current", item.get("version") == local.version)
    return sorted(versions, key=lambda x: (x.get("code", -1), x.get("version", "")), reverse=True)


def _version_root() -> Path:
    root = Path(os.getenv("KRBI_VERSIONS_DIR", Path.home() / ".krbi" / "versions"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def install_version(version: str, timeout: float = 30.0) -> Path:
    version = version.strip()
    if not version or "/" in version or any(ch in version for ch in "\\"):
        raise UpdateError("invalid version")
    match = next((v for v in fetch_versions(timeout) if v.get("version") == version), None)
    if not match:
        raise UpdateError(f"version {version} is not listed in versions.json")
    commit = str(match["commit"]).strip()
    if len(commit) < 7 or any(c not in "0123456789abcdefABCDEF" for c in commit):
        raise UpdateError("invalid version commit")
    destination = _version_root() / version
    marker = destination / "update.txt"
    if marker.exists():
        return destination
    temp = Path(tempfile.mkdtemp(prefix=f".{version}-", dir=str(_version_root())))
    archive = temp / "source.zip"
    try:
        request = Request(GITHUB_ARCHIVE_URL.format(commit=commit), headers={"User-Agent": "KRBI-Agent-Updater/1.1"})
        with urlopen(request, timeout=timeout) as response, archive.open("wb") as out:
            shutil.copyfileobj(response, out)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(temp / "extract")
        roots = [p for p in (temp / "extract").iterdir() if p.is_dir()]
        if len(roots) != 1:
            raise UpdateError("unexpected GitHub archive layout")
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(roots[0]), str(destination))
        (destination / ".krbi-version-commit").write_text(commit + "\n", encoding="utf-8")
        return destination
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def _git_root() -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True, text=True, timeout=5, check=True,
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
