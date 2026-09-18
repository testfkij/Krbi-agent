from __future__ import annotations

import json
import secrets
from typing import Any

from . import __version__
from .settings import Settings
from .tools import ToolExecutor

MCP_VERSION = "2026-07-28"
LEGACY_MCP_VERSION = "2025-11-25"

def ensure_mcp_token(settings: Settings) -> str:
    token = settings.mcp_token.strip()
    if token:
        return token
    token = secrets.token_urlsafe(32)
    settings.mcp_token = token
    return token

def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

def handle_mcp_request(payload: dict[str, Any], settings: Settings, tools: ToolExecutor) -> tuple[int, dict[str, str], dict[str, Any]]:
    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}
    if payload.get("jsonrpc") != "2.0":
        return 400, {}, _error(request_id, -32600, "JSON-RPC 2.0 is required")
    if method in {"initialize", "server/discover"}:
        requested = str(params.get("protocolVersion", ""))
        protocol = requested if requested in {LEGACY_MCP_VERSION, MCP_VERSION} else MCP_VERSION
        return 200, {"MCP-Protocol-Version": protocol}, {
            "jsonrpc": "2.0", "id": request_id,
            "result": {
                "protocolVersion": protocol,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "krbi-agent", "version": __version__},
            },
        }
    if method in {"ping"}:
        return 200, {}, {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method in {"tools/list", "list_tools"}:
        return 200, {}, {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools.schemas()}}
    if method in {"tools/call", "call_tool"}:
        name = str(params.get("name", "")).strip()
        args = params.get("arguments") or {}
        try:
            spec = tools.registry.get(name)
        except KeyError:
            return 200, {}, _error(request_id, -32602, f"unknown tool: {name}")
        allowed = settings.tool_allowed(name, spec.dangerous)
        if spec.dangerous and not allowed:
            return 200, {}, _error(request_id, -32001, f"tool '{name}' requires local approval")
        try:
            result = __import__("asyncio").run(tools.call(name, args, allowed))
        except Exception as exc:
            return 200, {}, _error(request_id, -32000, str(exc))
        return 200, {}, {
            "jsonrpc": "2.0", "id": request_id,
            "result": {"content": [{"type": "text", "text": json.dumps(result, default=str)}]},
        }
    return 200, {}, _error(request_id, -32601, f"method not found: {method}")

def connection_info(base_url: str, settings: Settings) -> dict[str, str]:
    token = ensure_mcp_token(settings)
    return {
        "endpoint": base_url.rstrip("/") + "/mcp",
        "authorization": f"Bearer {token}",
        "protocol": MCP_VERSION,
    }
