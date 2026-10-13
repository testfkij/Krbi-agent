"""User-owned declarative custom tools; model-generated Python is never executed."""
from __future__ import annotations
import json
import re
from pathlib import Path
from urllib.parse import quote
from typing import Any
from .core import ChatMessage
from .tools import ToolSpec

TOOL_FILE = Path.home() / ".krbi" / "custom_tools.json"
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,47}$")
ALLOWED_KINDS = {"text_template", "json_lookup", "url_encode", "word_count"}
BUILTIN_NAMES = {"clock", "system_info", "read_file", "list_dir", "search_files", "file_exists", "write_file", "shell"}

def load_definitions(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or TOOL_FILE
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError):
        return []
    if not isinstance(raw, list):
        return []
    output = []
    for item in raw:
        try:
            output.append(validate_definition(item))
        except (ValueError, TypeError):
            continue
    return output

def validate_definition(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise TypeError("tool definition must be an object")
    name = str(item.get("name", "")).strip().lower()
    if not NAME_RE.fullmatch(name):
        raise ValueError("tool name must match [a-z][a-z0-9_]{1,47}")
    if name in BUILTIN_NAMES:
        raise ValueError("custom tools may not replace built-in tools")
    description = str(item.get("description", "")).strip()
    if not description or len(description) > 500:
        raise ValueError("description must be 1–500 characters")
    kind = str(item.get("kind", "")).strip()
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"kind must be one of: {', '.join(sorted(ALLOWED_KINDS))}")
    definition: dict[str, Any] = {"name": name, "description": description, "kind": kind}
    if kind == "text_template":
        template = str(item.get("template", "{value}"))
        if len(template) > 4000:
            raise ValueError("template too long")
        definition["template"] = template
    elif kind == "json_lookup":
        definition["path"] = str(item.get("path", "")).strip()[:300]
    return definition

def _make_spec(item: dict[str, Any]) -> ToolSpec:
    item = validate_definition(item)
    name, kind = item["name"], item["kind"]
    if kind == "text_template":
        template = item["template"]
        async def invoke(args):
            value = str(args.get("value", ""))
            return {"tool": name, "result": template.replace("{value}", value)}
        schema = {"type": "object", "properties": {"value": {"type": "string", "description": "Input value"}}, "required": ["value"]}
    elif kind == "json_lookup":
        path = item["path"]
        async def invoke(args):
            value: Any = args.get("data")
            if isinstance(value, str):
                try: value = json.loads(value)
                except ValueError as exc: return {"error": f"data is not valid JSON: {exc}"}
            for part in path.split(".") if path else []:
                if isinstance(value, dict) and part in value: value = value[part]
                elif isinstance(value, list) and part.isdigit() and int(part) < len(value): value = value[int(part)]
                else: return {"error": f"path not found: {path}"}
            return {"path": path, "result": value}
        schema = {"type": "object", "properties": {"data": {"type": ["string", "object", "array"]}}, "required": ["data"]}
    elif kind == "url_encode":
        async def invoke(args):
            return {"result": quote(str(args.get("value", "")), safe="")}
        schema = {"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]}
    else:
        async def invoke(args):
            value = str(args.get("value", ""))
            return {"words": len(value.split()), "characters": len(value)}
        schema = {"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]}
    return ToolSpec(name, item["description"], schema, invoke, False)

def register_custom_tools(registry, path: Path | None = None) -> list[str]:
    added = []
    for definition in load_definitions(path):
        try:
            registry.register(_make_spec(definition))
            added.append(definition["name"])
        except (ValueError, TypeError):
            continue
    return added

def save_definition(definition: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    target = path or TOOL_FILE
    clean = validate_definition(definition)
    items = load_definitions(target)
    if any(item["name"] == clean["name"] for item in items):
        raise ValueError(f"custom tool already exists: {clean['name']}")
    target.parent.mkdir(parents=True, exist_ok=True)
    items.append(clean)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(target)
    return clean

async def build_definition_from_prompt(provider, model: str, request: str, api_key: str | None = None) -> dict[str, Any]:
    """Use the configured model to design a tool using a safe, bounded declarative format."""
    instructions = (
        "Design one useful KRBI custom tool as JSON only. Allowed kinds: text_template "
        "(template may contain {value}), json_lookup (path is a dot-separated path), "
        "url_encode, word_count. Never propose Python, shell, network access, filesystem writes, "
        "or arbitrary code. JSON keys: name, description, kind, plus template or path if needed. "
        "Tool name regex: ^[a-z][a-z0-9_]{1,47}$. Keep tool narrowly scoped."
    )
    parts = []
    async for event in provider.stream_chat(
        [ChatMessage("system", instructions), ChatMessage("user", request)],
        model, tools=[], temperature=0.1, max_tokens=700,
    ):
        if event.type == "delta":
            parts.append(event.delta)
    raw = "".join(parts).strip()
    raw = re.sub(r"^\`\`\`(?:json)?\s*", "", raw, flags=re.I)
    raw = re.sub(r"\s*\`\`\`$", "", raw)
    try:
        return validate_definition(json.loads(raw))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"model did not return a valid custom tool JSON object: {exc}") from exc
