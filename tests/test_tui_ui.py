import asyncio

from krbi_agent.settings import Settings
from krbi_agent import textual_app


def test_tui_settings_controls(monkeypatch):
    monkeypatch.setattr(textual_app, "load_settings", lambda: Settings())
    monkeypatch.setattr(textual_app, "save_settings", lambda settings: None)

    async def run():
        app = textual_app.KRBIApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.open_settings()
            await pilot.pause()
            assert app.query_one("#settings_view").styles.display == "block"
            await pilot.click("#approval_plan")
            await pilot.pause()
            assert app.settings.approval_mode == "plan"
            await pilot.click("#tool_shell")
            await pilot.pause()
            assert "shell" in app.settings.approved_tools
            await pilot.click("#settings_close")
            await pilot.pause()
            assert app.query_one("#settings_view").styles.display == "none"
            app.reset_session()
            await pilot.pause()
            assert app.provider is None
            assert app.model is None

    asyncio.run(run())
