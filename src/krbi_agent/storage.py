"""Durable SQLite conversation store with readable Markdown exports."""
from __future__ import annotations
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from .core import ChatMessage, Usage

@dataclass(slots=True)
class Chat:
    id: int
    title: str
    provider: str
    model: str
    messages: list[ChatMessage] = field(default_factory=list)
    usages: list[Usage] = field(default_factory=list)
    path: Path | None = None
    created_at: str = ""

class Store:
    """Persist conversations in SQLite and retain Markdown files for export."""
    def __init__(self, root=None, db_path=None):
        custom_root = root is not None
        self.root = Path(root or Path.home() / ".krbi" / "chats").expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path).expanduser() if db_path else (
            self.root / "krbi.sqlite3" if custom_root else self.root.parent / "krbi.sqlite3"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._init_db()

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=15000")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS chats (
              id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
              provider TEXT NOT NULL, model TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              role TEXT NOT NULL, content TEXT NOT NULL, name TEXT,
              tool_call_id TEXT, tool_calls_json TEXT
            );
            CREATE INDEX IF NOT EXISTS messages_chat_idx ON messages(chat_id, id);
            CREATE TABLE IF NOT EXISTS usage (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              prompt_tokens INTEGER NOT NULL DEFAULT 0,
              completion_tokens INTEGER NOT NULL DEFAULT 0, total_tokens INTEGER NOT NULL DEFAULT 0
            );
            """)

    def _markdown_path(self, cid):
        return self.root / f"chat-{int(cid):06d}.md"

    def _path_for(self, cid):
        path = self._markdown_path(cid)
        if path.exists():
            return path
        alternatives = sorted(self.root.glob(f"chat-{int(cid):06d}-*.md"))
        return alternatives[-1] if alternatives else path

    def _append(self, cid, text):
        with self._path_for(cid).open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")

    def new_chat(self, title, provider, model):
        created = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as db:
            cur = db.execute(
                "INSERT INTO chats(title,provider,model,created_at) VALUES(?,?,?,?)",
                (str(title)[:200], str(provider)[:120], str(model)[:240], created),
            )
            cid = int(cur.lastrowid)
            path = self._markdown_path(cid)
            if path.exists():
                path = self.root / f"chat-{cid:06d}-{datetime.now().strftime('%H%M%S%f')}.md"
            path.write_text(
                f"# {title}\n\n- Provider: `{provider}`\n- Model: `{model}`\n- Created: `{created}`\n\n---\n",
                encoding="utf-8",
            )
        return cid

    def add_message(self, chat_id, message):
        cid = int(chat_id)
        encoded = json.dumps(message.tool_calls, ensure_ascii=False) if message.tool_calls else None
        with self._lock, self._connect() as db:
            db.execute(
                "INSERT INTO messages(chat_id,role,content,name,tool_call_id,tool_calls_json) VALUES(?,?,?,?,?,?)",
                (cid, message.role, message.content, message.name, message.tool_call_id, encoded),
            )
        self._append(cid, f"## {message.role.upper()}\n\n{message.content}\n")

    def add_usage(self, chat_id, usage):
        cid = int(chat_id)
        with self._lock, self._connect() as db:
            db.execute(
                "INSERT INTO usage(chat_id,prompt_tokens,completion_tokens,total_tokens) VALUES(?,?,?,?)",
                (cid, int(usage.prompt_tokens), int(usage.completion_tokens), int(usage.total_tokens)),
            )
        self._append(cid, f"## USAGE\n\n- Prompt tokens: {usage.prompt_tokens}\n- Completion tokens: {usage.completion_tokens}\n- Total tokens: {usage.total_tokens}\n")

    def messages(self, chat_id):
        with self._connect() as db:
            rows = db.execute(
                "SELECT role,content,name,tool_call_id,tool_calls_json FROM messages WHERE chat_id=? ORDER BY id",
                (int(chat_id),),
            ).fetchall()
        output = []
        for row in rows:
            try:
                calls = json.loads(row["tool_calls_json"]) if row["tool_calls_json"] else None
            except (ValueError, TypeError):
                calls = None
            output.append(ChatMessage(row["role"], row["content"], row["name"], row["tool_call_id"], calls))
        return output

    def usage(self, chat_id):
        with self._connect() as db:
            rows = db.execute(
                "SELECT prompt_tokens,completion_tokens,total_tokens FROM usage WHERE chat_id=? ORDER BY id",
                (int(chat_id),),
            ).fetchall()
        return [Usage(int(r[0]), int(r[1]), int(r[2])) for r in rows]

    def chats(self):
        with self._connect() as db:
            rows = db.execute("SELECT id,title,provider,model,created_at FROM chats ORDER BY id").fetchall()
        return [
            Chat(int(r["id"]), r["title"], r["provider"], r["model"],
                 self.messages(int(r["id"])), self.usage(int(r["id"])),
                 self._path_for(int(r["id"])), r["created_at"])
            for r in rows
        ]

    def delete(self, chat_id):
        cid = int(chat_id)
        with self._lock, self._connect() as db:
            db.execute("DELETE FROM chats WHERE id=?", (cid,))
        for path in [self._markdown_path(cid), *self.root.glob(f"chat-{cid:06d}-*.md")]:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    def export(self, chat_id):
        path = self._path_for(int(chat_id))
        if path.exists():
            return path.read_text(encoding="utf-8")
        chat = next((item for item in self.chats() if item.id == int(chat_id)), None)
        if chat is None:
            raise KeyError(f"chat {chat_id} does not exist")
        return "\n".join([f"# {chat.title}", "", f"- Provider: `{chat.provider}`",
                          f"- Model: `{chat.model}`", "",
                          *[f"## {m.role.upper()}\n\n{m.content}\n" for m in chat.messages]])
