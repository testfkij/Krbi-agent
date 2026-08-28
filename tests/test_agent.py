import asyncio
import tempfile

from krbi_agent.agent import Agent
from krbi_agent.core import StreamEvent
from krbi_agent.storage import Store


class FakeProvider:
    def __init__(self):
        self.n = 0
        self.tool_rounds = []

    async def stream_chat(self, messages, model, **kwargs):
        self.n += 1
        self.tool_rounds.append(bool(kwargs.get("tools")))
        if self.n == 1:
            assert kwargs.get("tools")
            yield StreamEvent(
                "tool_call_delta",
                tool_calls=[
                    {
                        "index": 0,
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "clock", "arguments": "{}"},
                    }
                ],
            )
            yield StreamEvent("done")
        else:
            assert kwargs.get("tools")
            assert any(m.role == "tool" for m in messages)
            yield StreamEvent("delta", delta="Done.")
            yield StreamEvent("done")


class Reg:
    def __init__(self):
        self.p = FakeProvider()

    def get(self, name, api_key=None):
        return self.p


async def run():
    with tempfile.TemporaryDirectory() as d:
        store = Store(d)
        cid = store.new_chat("t", "fake", "m")
        events = []
        registry = Reg()
        async for event in Agent(registry, store).run(
            cid, "fake", "m", "what time?", allow_dangerous=False
        ):
            events.append(event)
        assert any(e.type == "tool_start" for e in events)
        assert any(e.type == "tool_result" for e in events)
        assert store.messages(cid)[-1].content == "Done."
        assert registry.p.tool_rounds == [True, True]


def test_agent_tool_loop():
    asyncio.run(run())
