from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    ok: bool
    detail: str


def _module(name: str) -> Check:
    return Check(name, importlib.util.find_spec(name) is not None, "installed" if importlib.util.find_spec(name) else "missing")


def run_checks() -> list[Check]:
    checks = [
        Check("Python", sys.version_info >= (3, 11), platform.python_version()),
        _module("httpx"),
        _module("rich"),
        _module("textual"),
    ]
    for name, executable in (
        ("git", "git"),
        ("cloudflared", "cloudflared"),
        ("localtunnel", "lt"),
        ("ngrok", "ngrok"),
        ("ssh", "ssh"),
    ):
        path = shutil.which(executable)
        checks.append(Check(name, path is not None, path or "not found"))
    try:
        from .providers import ProviderRegistry
        registry = ProviderRegistry()
        checks.append(Check("providers", bool(registry.names()), f"{len(registry.names())} configured defaults"))
    except Exception as exc:
        checks.append(Check("providers", False, str(exc)))
    settings_path = os.getenv("KRBI_SETTINGS", "~/.krbi/settings.toml")
    checks.append(Check("settings path", True, settings_path))
    return checks
