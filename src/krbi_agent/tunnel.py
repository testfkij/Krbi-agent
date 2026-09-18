from __future__ import annotations

import os
import platform
import queue
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

URL_RE = re.compile(r"https?://[A-Za-z0-9._:-]+(?:/[^\s]*)?")

@dataclass(frozen=True, slots=True)
class TunnelProvider:
    name: str
    executable: str
    custom_subdomain: bool
    build_command: object
    hint: str

PROVIDERS = {
    "cloudflared": TunnelProvider(
        "cloudflared", "cloudflared", False,
        lambda exe, port, sub: [exe, "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"],
        "Quick tunnel URL is generated automatically; custom subdomains require a managed Cloudflare tunnel.",
    ),
    "localtunnel": TunnelProvider(
        "localtunnel", "lt", True,
        lambda exe, port, sub: [exe, "--port", str(port)] + ([ "--subdomain", sub ] if sub else []),
        "Requires the localtunnel/lt CLI; custom subdomain depends on availability.",
    ),
    "ngrok": TunnelProvider(
        "ngrok", "ngrok", True,
        lambda exe, port, sub: [exe, "http", str(port)] + ([ "--domain", sub ] if sub else []),
        "A custom domain must be reserved/configured in ngrok.",
    ),
    "serveo": TunnelProvider(
        "serveo", "ssh", True,
        lambda exe, port, sub: [exe, "-o", "StrictHostKeyChecking=no", "-o", "ExitOnForwardFailure=yes",
                                "-R", f"{sub or 'krbi'}:80:127.0.0.1:{port}", "serveo.net"],
        "Uses SSH remote forwarding; the chosen subdomain may be unavailable.",
    ),
}

class TunnelError(RuntimeError):
    pass

class TunnelManager:
    def __init__(self, state_path: Path | None = None):
        self.state_path = state_path or Path.home() / ".krbi" / "tunnel.toml"
        self.process: subprocess.Popen[str] | None = None
        self.url: str | None = None
        self.provider: str | None = None
        self.subdomain: str = ""
        self.port: int = 8787
        self._reader_thread: threading.Thread | None = None
        self._lines: queue.Queue[str] = queue.Queue()

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def load(self) -> dict[str, str]:
        if not self.state_path.exists():
            return {}
        import tomllib
        try:
            return {str(k): str(v) for k, v in tomllib.loads(self.state_path.read_text(encoding="utf-8")).get("tunnel", {}).items()}
        except Exception:
            return {}

    def save(self, *, provider: str, subdomain: str, port: int, url: str | None = None, pid: int = 0) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        values = [
            "[tunnel]",
            f'provider = "{provider.replace(chr(34), chr(92)+chr(34))}"',
            f'subdomain = "{subdomain.replace(chr(34), chr(92)+chr(34))}"',
            f"port = {int(port)}",
            f"pid = {int(pid)}",
        ]
        if url:
            values.append(f'last_url = "{url.replace(chr(34), chr(92)+chr(34))}"')
        self.state_path.write_text("\n".join(values) + "\n", encoding="utf-8")

    def configure(self, provider: str | None = None, subdomain: str | None = None, port: int | None = None) -> dict[str, str]:
        old = self.load()
        self.provider = provider or old.get("provider") or "cloudflared"
        if self.provider not in PROVIDERS:
            raise TunnelError(f"unsupported tunnel provider: {self.provider}")
        self.subdomain = subdomain if subdomain is not None else old.get("subdomain", "")
        self.port = int(port if port is not None else old.get("port", 8787))
        if not (1 <= self.port <= 65535):
            raise TunnelError("port must be between 1 and 65535")
        self.save(provider=self.provider, subdomain=self.subdomain, port=self.port, url=old.get("last_url"))
        return {"provider": self.provider, "subdomain": self.subdomain, "port": str(self.port)}

    def start(self, provider: str | None = None, subdomain: str | None = None, port: int | None = None, timeout: float = 12.0) -> str:
        self.stop()
        cfg = self.configure(provider, subdomain, port)
        spec = PROVIDERS[cfg["provider"]]
        exe = shutil.which(spec.executable)
        if not exe:
            raise TunnelError(f"{spec.executable!r} is not installed or not on PATH")
        command = spec.build_command(exe, self.port, self.subdomain)
        env = os.environ.copy()
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if platform.system() == "Windows" else 0
        self.process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            start_new_session=(platform.system() != "Windows"), creationflags=creationflags, env=env,
        )
        self.provider = self.provider or cfg["provider"]
        self.url = None
        self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self._reader_thread.start()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.url:
                self.save(provider=self.provider, subdomain=self.subdomain, port=self.port, url=self.url, pid=self.process.pid if self.process else 0)
                return self.url
            if self.process.poll() is not None:
                break
            time.sleep(0.1)
        output = []
        while True:
            try:
                output.append(self._lines.get_nowait())
            except queue.Empty:
                break
        raise TunnelError(f"tunnel did not report a public URL. {' '.join(output)[-800:]}")

    def _read_output(self) -> None:
        if not self.process or not self.process.stdout:
            return
        for line in self.process.stdout:
            clean = line.strip()
            if clean:
                self._lines.put(clean)
                matches = URL_RE.findall(clean)
                for candidate in matches:
                    if "127.0.0.1" not in candidate and "localhost" not in candidate:
                        self.url = candidate.rstrip(".,")
                        return

    def stop(self) -> None:
        proc = self.process
        self.process = None
        self.url = None
        stored = self.load()
        if proc is not None:
            try:
                proc.terminate(); proc.wait(timeout=3)
            except Exception:
                try: proc.kill()
                except Exception: pass
        else:
            raw_pid = stored.get("pid", "0")
            try: pid = int(raw_pid)
            except ValueError: pid = 0
            if pid > 0:
                try:
                    if platform.system() == "Windows":
                        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=5, check=False)
                    else:
                        os.kill(pid, 15)
                except OSError:
                    pass
        if stored:
            self.save(provider=stored.get("provider", self.provider or "cloudflared"), subdomain=stored.get("subdomain", self.subdomain), port=int(stored.get("port", self.port)), url=stored.get("last_url", self.url), pid=0)

    def status(self) -> dict[str, object]:
        stored = self.load()
        provider = self.provider or stored.get("provider") or "cloudflared"
        running = self.is_running
        if not running and stored.get("pid"):
            try:
                os.kill(int(stored["pid"]), 0)
                running = True
            except (OSError, ValueError):
                running = False
        return {
            "running": running,
            "provider": provider,
            "subdomain": self.subdomain or stored.get("subdomain", ""),
            "port": self.port or int(stored.get("port", "8787")),
            "url": self.url or stored.get("last_url", ""),
            "platform": platform.system(),
            "hint": PROVIDERS[provider].hint if provider in PROVIDERS else "",
            "custom_subdomain": PROVIDERS[provider].custom_subdomain if provider in PROVIDERS else False,
        }
