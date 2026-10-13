"""Explicit, scoped KRBI Agent uninstaller."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

APP_ROOT = Path.home() / ".krbi"
USER_SERVICE_DIR = Path.home() / ".config" / "systemd" / "user"

def _service_files() -> list[Path]:
    if not USER_SERVICE_DIR.is_dir():
        return []
    return [p for p in USER_SERVICE_DIR.glob("krbi*.service") if p.is_file()]

def uninstall(*, yes: bool = False, keep_data: bool = False, remove_checkout: bool = False) -> int:
    print("KRBI Agent uninstaller")
    print(f"  settings, chats, database and tunnel state: {'keep' if keep_data else APP_ROOT}")
    print(f"  checkout: {'remove (explicitly requested)' if remove_checkout else 'keep'}")
    service_files = _service_files()
    if service_files:
        print("  user service files: " + ", ".join(str(p) for p in service_files))
    if not yes:
        try:
            answer = input('Type "KRBI" to confirm uninstall: ').strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled; nothing was removed.")
            return 1
        if answer != "KRBI":
            print("Cancelled; nothing was removed.")
            return 1

    # Stop an active tunnel before clearing its persisted PID record.
    try:
        from .tunnel import TunnelManager
        TunnelManager().stop()
    except Exception as exc:
        print(f"Note: tunnel stop reported: {exc}")

    removed = []
    if not keep_data and APP_ROOT.exists():
        shutil.rmtree(APP_ROOT)
        removed.append(str(APP_ROOT))
    for service in service_files:
        try:
            service.unlink()
            removed.append(str(service))
        except OSError as exc:
            print(f"Could not remove {service}: {exc}")

    # Uninstall only the package installed in the active interpreter. No shell is used.
    try:
        check = subprocess.run(
            [sys.executable, "-m", "pip", "show", "krbi-agent"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if check.returncode == 0:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", "krbi-agent"],
                capture_output=True, text=True, timeout=60, check=False,
            )
            if result.returncode == 0:
                removed.append("krbi-agent Python package in " + sys.executable)
            else:
                print("Package uninstall did not complete: " + (result.stderr or result.stdout)[-1200:])
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Could not run pip uninstall: {exc}")

    if remove_checkout:
        cwd = Path.cwd().resolve()
        gitdir = cwd / ".git"
        if not gitdir.is_dir():
            print("Checkout removal skipped: run this argument from the KRBI git checkout.")
        else:
            import subprocess as sp
            remote = sp.run(["git", "-C", str(cwd), "remote", "get-url", "origin"], capture_output=True, text=True, timeout=10, check=False)
            url = remote.stdout.strip().lower()
            if "github.com/testfkij/krbi-agent" not in url:
                print("Checkout removal skipped: origin does not match testfkij/krbi-agent.")
            else:
                parent = cwd.parent
                print("Checkout path verified: " + str(cwd))
                # Remove only the current, explicitly selected checkout after package work.
                shutil.rmtree(cwd)
                removed.append(str(cwd))
                print(f"Removed repository checkout. Parent directory preserved: {parent}")

    print("KRBI uninstall finished.")
    if removed:
        for entry in removed:
            print("Removed: " + entry)
    else:
        print("No matching installed package or data paths were found.")
    if keep_data:
        print("User data was preserved.")
    return 0

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="krbi uninstall", description="Remove KRBI Agent from this user environment.")
    parser.add_argument("--yes", action="store_true", help="Skip the confirmation prompt.")
    parser.add_argument("--keep-data", action="store_true", help="Preserve ~/.krbi settings, chats, database and custom tools.")
    parser.add_argument("--remove-checkout", action="store_true", help="Also delete the current checkout, only if origin matches testfkij/krbi-agent.")
    args = parser.parse_args(argv)
    return uninstall(yes=args.yes, keep_data=args.keep_data, remove_checkout=args.remove_checkout)

if __name__ == "__main__":
    raise SystemExit(main())
