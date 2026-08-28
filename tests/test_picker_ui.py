import asyncio
from krbi_agent.ui import Picker

def test_picker_filters_and_selects():
    async def run():
        app = Picker("Providers", ["OpenAI", "Ollama", "LM Studio"])
        async with app.run_test(size=(100, 32)) as pilot:
            await pilot.pause()
            search = app.query_one("#search")
            search.value = "oll"
            await pilot.pause()
            assert app.filtered == ["Ollama"]
            search.focus()
            await pilot.press("enter")
        assert app.return_value == "Ollama"
    asyncio.run(run())
