from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Command:
    name: str
    description: str
    action: str

COMMANDS = [
    Command("/help", "Show commands", "help"),
    Command("/focus", "Stay on a task until it is completed", "focus"),
    Command("/unfocus", "Release focus mode", "unfocus"),
    Command("/role", "Choose or show the active specialist role", "role"),
    Command("/skills", "List loaded skill files", "skills"),
    Command("/tool-build", "Ask the current model to design a safe custom tool", "tool-build"),
    Command("/goal", "Set or show the current agent goal", "goal"),
    Command("/system", "Set system prompt", "system"),
    Command("/provider", "Select a provider", "provider"),
    Command("/model", "Select or search live models", "model"),
    Command("/local", "Show or use local model providers", "local"),
    Command("/providers", "List providers", "providers"),
    Command("/models", "Refresh/search live models", "models"),
    Command("/tools", "List available tools", "tools"),
    Command("/approve", "Approve a tool for future calls", "approve"),
    Command("/revoke", "Revoke a tool approval", "revoke"),
    Command("/approval", "Set tool approval mode", "approval"),
    Command("/settings", "Open KRBI settings", "settings"),
    Command("/mcp", "Inspect MCP tools/connection", "mcp"),
    Command("/tunnel", "Show tunnel status", "tunnel"),
    Command("/benchmark", "Benchmark models", "benchmark"),
    Command("/banner", "Set or show the UI banner", "banner"),
    Command("/new", "Start a new chat", "new"),
    Command("/clear", "Clear transcript", "clear"),
    Command("/reset", "Reset the current session", "reset"),
    Command("/history", "Show chat history", "history"),
    Command("/tokens", "Show token usage", "tokens"),
    Command("/export", "Export current chat", "export"),
    Command("/quit", "Exit KRBI Agent (unfocus first)", "quit"),
]

def search_commands(q: str) -> list[Command]:
    q = q.lower().lstrip("/")
    return [command for command in COMMANDS if q in command.name.lower() or q in command.description.lower()]
