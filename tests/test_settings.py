from pathlib import Path

from krbi_agent.settings import APPROVAL_MODES, Settings, load_settings, save_settings


def test_settings_round_trip_and_validation(tmp_path: Path):
    path = tmp_path / "settings.toml"
    settings = Settings(approval_mode="not-a-mode", approved_tools={"shell"}, stream_redraw_ms=9999)
    assert settings.approval_mode == "default"
    assert settings.stream_redraw_ms == 500
    save_settings(settings, path)
    loaded = load_settings(path)
    assert loaded.approval_mode in APPROVAL_MODES
    assert loaded.approved_tools == {"shell"}
    assert loaded.stream_redraw_ms == 500


def test_tool_approval_modes():
    settings = Settings()
    assert settings.tool_allowed("read_file", False)
    assert not settings.tool_allowed("shell", True)
    settings.approved_tools.add("shell")
    assert settings.tool_allowed("shell", True)
    settings.approved_tools.remove("shell")
    settings.approval_mode = "auto_edit"
    assert settings.tool_allowed("write_file", True)
    assert not settings.tool_allowed("shell", True)
    settings.approval_mode = "yolo"
    assert settings.tool_allowed("shell", True)
