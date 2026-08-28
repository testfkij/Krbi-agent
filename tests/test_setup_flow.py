import asyncio

from krbi_agent import textual_app
from krbi_agent.core import ModelInfo
from krbi_agent.providers import ProviderConfig
from krbi_agent.settings import Settings


class FakeProvider:
    async def list_models(self):
        return [
            ModelInfo("openrouter", "free-a", capabilities={"chat", "streaming"}),
            ModelInfo("openrouter", "free-b", capabilities={"chat", "tools"}),
        ]


class FakeRegistry:
    def __init__(self, *_args, **_kwargs):
        self.configs = {
            "openrouter": ProviderConfig("openrouter"),
            "ollama": ProviderConfig("ollama", base_url="http://127.0.0.1:11434/v1"),
            "lm-studio": ProviderConfig("lm-studio", base_url="http://127.0.0.1:1234/v1"),
        }

    def names(self):
        return list(self.configs)

    def get(self, name, api_key=None):
        assert name in self.configs
        assert api_key in {"", "secret-test-key"}
        return FakeProvider()


def test_full_provider_key_model_flow(monkeypatch):
    monkeypatch.setattr(textual_app, "ProviderRegistry", FakeRegistry)
    monkeypatch.setattr(textual_app, "load_settings", lambda: Settings())
    monkeypatch.setattr(textual_app, "save_settings", lambda settings: None)

    async def run():
        app = textual_app.KRBIApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app.query_one("#composer")
            assert app.query_one("#setup_overlay").styles.display == "none"

            app._handle_slash("/provider")
            await pilot.pause()
            assert app.query_one("#setup_overlay").styles.display == "block"
            assert app.query_one("#provider_picker").styles.display == "block"
            assert app.query_one("#api_key_panel").styles.display == "none"
            assert not app.query("#key")

            search = app.query_one("#provider_picker_search")
            search.value = "router"
            await pilot.pause()
            await pilot.press("down")
            await pilot.pause()
            assert app.query_one("#provider_picker_list").has_focus
            await pilot.press("enter")
            await pilot.pause()
            assert app.query_one("#provider_picker").styles.display == "none"
            assert app.query_one("#api_key_panel").styles.display == "block"

            key = app.query_one("#setup_key")
            key.value = "secret-test-key"
            await pilot.press("enter")
            await pilot.pause(0.2)
            assert app.query_one("#model_picker").styles.display == "block"
            assert app.query_one("#api_key_panel").styles.display == "none"
            assert [v for _l, v in app.query_one("#model_picker").items] == ["free-a", "free-b"]

            model_search = app.query_one("#model_picker_search")
            model_search.value = "free-b"
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert app.query_one("#setup_overlay").styles.display == "none"
            assert app.provider == "openrouter"
            assert app.model == "free-b"
            assert app.api_keys["openrouter"] == "secret-test-key"
            assert not app.query("#api_key")
            assert app.query_one("#composer").has_focus

    asyncio.run(run())
