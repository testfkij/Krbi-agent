"""Specialist routing and skill loading for KRBI Agent."""
from __future__ import annotations
import re
from pathlib import Path

ROLE_LABELS = {
    "talker": "Conversation specialist",
    "web-developer": "Web development specialist",
    "backend-developer": "Backend and API specialist",
    "frontend-developer": "Frontend and TSX specialist",
    "designer": "Product and interaction designer",
    "coder": "General software engineer",
    "reviewer": "Code reviewer and security auditor",
    "fixer": "Bug and regression fixer",
    "builder": "Implementation and integration builder",
    "tool-builder": "Custom tool designer",
    "task-manager": "Task planning and assignment specialist",
}
ROLE_RULES = [
    ("tool-builder", ("custom tool", "build a tool", "create a tool", "new tool", "tool builder")),
    ("task-manager", ("assign task", "assign tasks", "task assignment", "split this task", "delegate")),
    ("reviewer", ("review", "audit", "security", "inspect", "vulnerability")),
    ("fixer", ("fix", "bug", "error", "crash", "broken", "regression", "not working")),
    ("designer", ("design", "ui", "ux", "layout", "visual", "interface", "responsive")),
    ("web-developer", ("website", "web app", "web development", "html", "css", "landing page")),
    ("frontend-developer", ("tsx", "react", "frontend", "front-end", "component", "chat scroll")),
    ("backend-developer", ("backend", "back-end", "api", "database", "sqlite", "server", "endpoint")),
    ("builder", ("build", "implement", "integrate", "add feature", "create feature")),
    ("coder", ("code", "python", "function", "refactor", "program")),
]

def normalize_role(role: str | None) -> str | None:
    value = (role or "").strip().lower().replace("_", "-").replace(" ", "-")
    return value if value in ROLE_LABELS else None

def assign_role(task: str, explicit_role: str | None = None) -> str:
    explicit = normalize_role(explicit_role)
    if explicit:
        return explicit
    text = re.sub(r"\s+", " ", task.lower())
    for role, terms in ROLE_RULES:
        if any(term in text for term in terms):
            return role
    return "talker"

def skill_directories() -> list[Path]:
    here = Path(__file__).resolve()
    candidates = [Path.cwd() / "skills", here.parents[2] / "skills", Path.home() / ".krbi" / "skills"]
    output = []
    for item in candidates:
        try:
            resolved = item.resolve()
        except OSError:
            continue
        if resolved not in output and resolved.is_dir():
            output.append(resolved)
    return output

def available_skills() -> list[dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for folder in skill_directories():
        for path in sorted(folder.glob("*.md")):
            key = path.stem.lower()
            found.setdefault(key, {"name": key, "path": str(path), "description": path.stem.replace("-", " ").title()})
    return list(found.values())

def load_skill(role: str) -> str:
    role = normalize_role(role) or "talker"
    aliases = {
        "web-developer": ("web-development", "web-developer"),
        "backend-developer": ("backend-development", "backend-developer"),
        "frontend-developer": ("frontend-development", "frontend-developer"),
        "designer": ("designer", "ui-ux-design"),
        "coder": ("coding", "coder"),
        "reviewer": ("reviewer", "code-review"),
        "fixer": ("error-fixer", "fixer"),
        "builder": ("builder", "implementation"),
        "tool-builder": ("tool-builder", "custom-tools"),
        "task-manager": ("task-assignment", "task-manager"),
        "talker": ("talker", "conversation"),
    }
    for folder in skill_directories():
        for alias in aliases.get(role, (role,)):
            path = folder / f"{alias}.md"
            try:
                if path.is_file():
                    return path.read_text(encoding="utf-8")[:12000]
            except OSError:
                continue
    return f"Act as the {ROLE_LABELS[role]}. Be concrete, careful, test claims, and report limitations honestly."
