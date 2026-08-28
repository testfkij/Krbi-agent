from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os

SETTINGS_PATH = Path(os.getenv("KRBI_SETTINGS", Path.home() / ".krbi" / "settings.toml"))
APPROVAL_MODES = ("default", "auto_edit", "plan", "yolo")

@dataclass(slots=True)
class Settings:
    approval_mode: str = "default"
    approved_tools: set[str] = field(default_factory=set)
    workspace: str = "."
    show_tool_events: bool = False
    stream_redraw_ms: int = 40
    default_provider: str | None = None
    default_model: str | None = None
    banner_text: str = "KRBI // AGENT"

    def __post_init__(self) -> None:
        if self.approval_mode not in APPROVAL_MODES:
            self.approval_mode = "default"
        self.stream_redraw_ms = min(max(int(self.stream_redraw_ms), 10), 500)

    @property
    def read_only(self) -> bool:
        return self.approval_mode == "plan"

    def tool_allowed(self, name: str, dangerous: bool) -> bool:
        if self.approval_mode == "yolo":
            return True
        if not dangerous:
            return True
        if self.approval_mode == "auto_edit" and name == "write_file":
            return True
        return name in self.approved_tools


def load_settings(path: Path = SETTINGS_PATH) -> Settings:
    if not path.exists():
        return Settings()
    import tomllib
    data = tomllib.loads(path.read_text(encoding="utf-8")).get("krbi", {})
    return Settings(
        approval_mode=str(data.get("approval_mode", "default")),
        approved_tools=set(data.get("approved_tools", [])),
        workspace=str(data.get("workspace", ".")),
        show_tool_events=bool(data.get("show_tool_events", False)),
        stream_redraw_ms=int(data.get("stream_redraw_ms", 40)),
        default_provider=data.get("default_provider"),
        default_model=data.get("default_model"),
        banner_text=str(data.get("banner_text", "KRBI // AGENT"))[:120] or "KRBI // AGENT",
    )


def save_settings(settings: Settings, path: Path = SETTINGS_PATH) -> None:
    settings.__post_init__()
    path.parent.mkdir(parents=True, exist_ok=True)
    approved = ", ".join('"' + x.replace('"', '\\"') + '"' for x in sorted(settings.approved_tools))
    def q(v: str) -> str:
        return '"' + v.replace('"', '\\"') + '"'
    lines = [
        "[krbi]",
        f"approval_mode = {q(settings.approval_mode)}",
        f"approved_tools = [{approved}]",
        f"workspace = {q(settings.workspace)}",
        f"show_tool_events = {str(settings.show_tool_events).lower()}",
        f"stream_redraw_ms = {settings.stream_redraw_ms}",
    ]
    if settings.default_provider:
        lines.append(f"default_provider = {q(settings.default_provider)}")
    if settings.default_model:
        lines.append(f"default_model = {q(settings.default_model)}")
    if settings.banner_text:
        lines.append(f"banner_text = {q(settings.banner_text[:120])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
