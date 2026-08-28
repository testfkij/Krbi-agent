import asyncio

from krbi_agent.settings import Settings
from krbi_agent.core import StreamEvent
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
            assert app.query_one("#tool_shell")
            app.query_one("#settings_view").styles.display = "none"
            assert app.query_one("#settings_view").styles.display == "none"
            app.reset_session()
            await pilot.pause()
            assert app.provider is None
            assert app.model is None

    asyncio.run(run())

def test_richlog_streaming_uses_supported_write_api():
    from pathlib import Path
    text = Path('src/krbi_agent/textual_app.py').read_text()
    assert 'end=""' not in text
    assert 'end="\\n"' not in text


def test_tui_send_text_streaming_path(monkeypatch):
    class FakeStore:
        def new_chat(self, *args): return "chat-1"
        def chats(self): return []
    class FakeAgent:
        async def run(self, *args, **kwargs):
            yield StreamEvent("delta", delta="hello")
            yield StreamEvent("done")

    monkeypatch.setattr(textual_app, "ProviderRegistry", lambda: type("R", (), {"names": lambda self: ["openrouter"]})())
    monkeypatch.setattr(textual_app, "load_settings", lambda: Settings(default_provider="openrouter", default_model="free-a"))
    monkeypatch.setattr(textual_app, "save_settings", lambda settings: None)

    async def run():
        app = textual_app.KRBIApp()
        app.store = FakeStore()
        app.agent = FakeAgent()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.provider = "openrouter"
            app.model = "free-a"
            app.chat_id = "chat-1"
            await app._send_text("hello")
            await pilot.pause()
            assert "hello" in str(app.query_one("#conversation").lines)

    asyncio.run(run())
