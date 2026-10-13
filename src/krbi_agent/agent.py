from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from .core import ChatMessage, StreamEvent, Usage, ToolCall
from .providers import ProviderRegistry
from .storage import Store
from .tools import ToolExecutor
from .settings import Settings, load_settings
from .queue import TaskQueue
from .roles import ROLE_LABELS, assign_role, load_skill

DEFAULT_SYSTEM = (
    "You are KRBI Agent, a capable general-purpose AI agent. Be accurate, useful, "
    "safe, and transparent about uncertainty. Use available tools when they materially "
    "help the user, verify actions, and never claim success without evidence."
)


class Agent:
    def __init__(self, registry=None, store=None, tools=None, settings: Settings | None = None, tool_workers=4):
        self.registry = registry or ProviderRegistry()
        self.store = store or Store()
        self.settings = settings or load_settings()
        self.tools = tools or ToolExecutor()
        self.tool_workers = max(1, int(tool_workers))

    def _tool_defs(self):
        return self.tools.schemas()

    async def run(
        self, chat_id, provider, model, prompt, system_prompt=None, goal=None,
        allow_dangerous=False, api_key=None, max_tool_rounds=8,
        focus_task: str | None = None, role: str | None = None, **params
    ) -> AsyncIterator[StreamEvent]:
        history = self.store.messages(chat_id)
        active_role = assign_role(focus_task or prompt, role)
        sys_prompt = system_prompt or DEFAULT_SYSTEM
        if goal:
            sys_prompt += f"\n\nCurrent user goal:\n{goal}"
        sys_prompt += (
            f"\n\nAssigned KRBI specialist: {active_role} "
            f"({ROLE_LABELS[active_role]}).\nSkill guidance:\n{load_skill(active_role)}"
        )
        if focus_task:
            sys_prompt += (
                "\n\nFOCUS MODE IS ACTIVE. The durable task objective is:\n"
                + focus_task
                + "\nStay on this objective until it is completed and verified. Do not ask routine "
                "clarifying questions; make safe, explicit assumptions and proceed. Break the work "
                "into steps internally, use available tools where appropriate, recover from errors, "
                "and verify the result before reporting completion. Never pretend an unverified step "
                "succeeded. If an external dependency blocks completion, explain the exact blocker and "
                "finish every independent part that can be done."
            )
        messages = [ChatMessage("system", sys_prompt), *history, ChatMessage("user", prompt)]
        self.store.add_message(chat_id, ChatMessage("user", prompt))
        final_parts = []
        last_usage = Usage()
        params = dict(params)
        params.setdefault("tools", self._tool_defs())

        for _ in range(max_tool_rounds):
            parts = []
            tool_acc = {}
            saw_tool = False
            try:
                async for event in self.registry.get(provider, api_key=api_key).stream_chat(messages, model, **params):
                    if event.type == "delta":
                        parts.append(event.delta)
                        yield event
                    elif event.type == "usage":
                        last_usage = event.usage or last_usage
                        yield event
                    elif event.type == "tool_call_delta":
                        saw_tool = True
                        for call in event.tool_calls:
                            index = call.get("index", 0)
                            current = tool_acc.setdefault(index, {
                                "id": call.get("id") or f"tool_{index}",
                                "name": None,
                                "arguments": "",
                            })
                            if call.get("id"):
                                current["id"] = call["id"]
                            fn = call.get("function") or {}
                            if fn.get("name"):
                                current["name"] = fn["name"]
                            if fn.get("arguments"):
                                current["arguments"] += fn["arguments"]
            except Exception as exc:
                yield StreamEvent("error", message=str(exc))
                return

            response_text = "".join(parts)
            final_parts.append(response_text)
            if not saw_tool:
                answer = "".join(final_parts)
                self.store.add_message(chat_id, ChatMessage("assistant", answer))
                if last_usage.total_tokens:
                    self.store.add_usage(chat_id, last_usage)
                yield StreamEvent("done", message=f"role={active_role}")
                return

            calls = []
            for item in tool_acc.values():
                try:
                    arguments = json.loads(item["arguments"] or "{}")
                    if not isinstance(arguments, dict):
                        raise ValueError("tool arguments must be a JSON object")
                except (json.JSONDecodeError, ValueError) as exc:
                    arguments = {"_raw": item["arguments"], "_parse_error": str(exc)}
                calls.append(ToolCall(item["id"], item["name"] or "unknown", arguments))

            assistant_calls = [
                {"id": call.id, "type": "function", "function": {
                    "name": call.name, "arguments": json.dumps(call.arguments)
                }}
                for call in calls
            ]
            messages.append(ChatMessage("assistant", response_text, tool_calls=assistant_calls))

            async def execute(call: ToolCall):
                try:
                    spec = self.tools.registry.get(call.name)
                    approved = allow_dangerous or self.settings.tool_allowed(call.name, spec.dangerous)
                    if spec.dangerous and not approved:
                        raise PermissionError(f"tool '{call.name}' is not approved; use /approve {call.name}")
                    return await self.tools.call(call, approved)
                except Exception as exc:
                    return {"error": str(exc)}

            queue = TaskQueue(execute, max_workers=min(self.tool_workers, max(1, len(calls))), max_pending=max(4, len(calls)))
            await queue.start()
            try:
                results = await asyncio.gather(*(queue.submit(call) for call in calls))
                for call, result in zip(calls, results):
                    yield StreamEvent("tool_start", message=call.name, raw={"tool_call": call.id})
                    yield StreamEvent("tool_result", message=call.name, raw={"tool_call": call.id, "result": result})
                    messages.append(ChatMessage("tool", json.dumps(result, default=str), name=call.name, tool_call_id=call.id))
            finally:
                await queue.close()

        yield StreamEvent("error", message=f"Agent stopped after {max_tool_rounds} tool rounds")
