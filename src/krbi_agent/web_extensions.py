"""Routes for the built TSX interface and task tools."""
from __future__ import annotations
import asyncio
import json
import mimetypes
from pathlib import Path
from . import web
from .config import add_provider
from .custom_tools import build_definition_from_prompt, save_definition, register_custom_tools
from .roles import ROLE_LABELS, available_skills, normalize_role, assign_role, load_skill

Handler = web.Handler
_old_get = Handler.do_GET
_old_post = Handler.do_POST
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

def _get(self):
    path = web.urlparse(self.path).path
    sid, _ = self._session()
    if path == "/" and (_DIST / "index.html").is_file():
        return self._send((_DIST / "index.html").read_text(encoding="utf-8"), ctype="text/html; charset=utf-8", sid=sid)
    if path.startswith("/assets/") and _DIST.is_dir():
        asset = (_DIST / path.lstrip("/")).resolve()
        if _DIST.resolve() in asset.parents and asset.is_file():
            return self._send(asset.read_text(encoding="utf-8"), ctype=mimetypes.guess_type(str(asset))[0] or "application/octet-stream", sid=sid)
    if path == "/roles":
        return self._send(json.dumps([{"id": k, "label": v} for k, v in ROLE_LABELS.items()]), ctype="application/json; charset=utf-8", sid=sid)
    if path == "/skills":
        return self._send(json.dumps(available_skills()), ctype="application/json; charset=utf-8", sid=sid)
    return _old_get(self)

def _post(self):
    path = web.urlparse(self.path).path
    if path == "/mcp":
        return _old_post(self)
    if path == "/chat/stream":
        return _chat_post(self)
    if path not in {"/session", "/providers/add", "/tools/build"}:
        return _old_post(self)
    sid, session = self._session()
    data = self._form()
    if path == "/providers/add":
        try:
            cfg = add_provider(data.get("name", ""), data.get("base_url", ""), data.get("api_key_env", ""), data.get("model", ""))
            web.REGISTRY.configs[cfg.name] = cfg
            return self._send(json.dumps({"ok": True, "provider": cfg.name}), ctype="application/json; charset=utf-8", sid=sid)
        except (ValueError, OSError) as exc:
            return self._send(str(exc), 400, sid=sid)
    if path == "/tools/build":
        request = data.get("request", "").strip()
        if not request or not session.provider or not session.model:
            return self._send("Describe a tool and connect a model before tool creation.", 400, sid=sid)
        try:
            client = web.REGISTRY.get(session.provider, api_key=session.api_key)
            spec = asyncio.run(build_definition_from_prompt(client, session.model, request))
            saved = save_definition(spec)
            register_custom_tools(web.AGENT.tools.registry)
            return self._send(json.dumps(saved, ensure_ascii=False), ctype="application/json; charset=utf-8", sid=sid)
        except Exception as exc:
            return self._send("Custom tool creation failed: " + str(exc), 400, sid=sid)

    if path == "/session":
        if data.get("reset") == "1":
            if session.focus_task:
                return self._send("focus is active; use /unfocus before reset", 409, sid=sid)
            session.provider = None
            session.model = None
            session.api_key = None
            session.chat_id = None
            session.goal = ""
            session.system = web.DEFAULT_SYSTEM
            session.role = None
            return self._send("session reset; saved chat history preserved", sid=sid)
        if data.get("new_chat") == "1":
            if session.focus_task:
                return self._send("focus is active; use /unfocus before a new chat", 409, sid=sid)
            session.chat_id = None
        if data.get("unfocus") == "1":
            session.focus_task = ""
        if "focus_task" in data:
            session.focus_task = data["focus_task"].strip()[:4000]
        if "goal" in data:
            session.goal = data["goal"].strip()[:4000]
        if "system" in data and data["system"].strip():
            session.system = data["system"].strip()[:12000]
        if "role" in data:
            selected = normalize_role(data["role"])
            if data["role"].strip() and not selected:
                return self._send("unknown specialist role", 400, sid=sid)
            session.role = selected
        return self._send(json.dumps({"ok": True, "focus": bool(session.focus_task), "role": session.role}), ctype="application/json; charset=utf-8", sid=sid)
    return _old_post(self)

def _chat_post(self):
    path = web.urlparse(self.path).path
    if path != "/chat/stream":
        return _old_post(self)
    sid, session = self._session()
    data = self._form()
    provider = data.get("provider") or session.provider
    model = data.get("model") or session.model
    prompt = data.get("prompt", "").strip()
    if not provider or not model or not prompt:
        return self._send("provider, model and prompt are required", 400, sid=sid)
    if provider not in web.REGISTRY.names():
        return self._send("unknown provider", 400, sid=sid)
    session.provider, session.model = provider, model
    if not session.chat_id:
        session.chat_id = web.STORE.new_chat("KRBI web chat", provider, model)
    self.send_response(200)
    self.send_header("content-type", "text/event-stream; charset=utf-8")
    self.send_header("cache-control", "no-cache, no-store")
    self.send_header("connection", "close")
    self.send_header("x-content-type-options", "nosniff")
    self.send_header("set-cookie", f"krbi_sid={sid}; Path=/; HttpOnly; SameSite=Strict")
    self.end_headers()
    async def run_agent():
        async for event in web.AGENT.run(
            session.chat_id, provider, model, prompt,
            system_prompt=session.system, goal=session.goal,
            api_key=session.api_key, focus_task=session.focus_task, role=session.role
        ):
            payload = None
            if event.type == "delta":
                payload = {"type": "delta", "text": event.delta}
            elif event.type == "tool_start":
                payload = {"type": "tool_start", "name": event.message}
            elif event.type == "tool_result":
                payload = {"type": "tool_result", "name": event.message}
            elif event.type == "error":
                payload = {"type": "error", "message": event.message}
            if payload is not None:
                self.wfile.write(("data: " + json.dumps(payload, ensure_ascii=False) + "\n\n").encode("utf-8"))
                self.wfile.flush()
    try:
        asyncio.run(run_agent())
    except (BrokenPipeError, ConnectionResetError):
        return

Handler.do_GET = _get
Handler.do_POST = _post
