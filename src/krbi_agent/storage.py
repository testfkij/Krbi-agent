from __future__ import annotations
from dataclasses import dataclass,field
from itertools import count
from pathlib import Path
from threading import RLock
from datetime import datetime,timezone
from .core import ChatMessage,Usage
@dataclass(slots=True)
class Chat:
 id:int; title:str; provider:str; model:str; messages:list[ChatMessage]=field(default_factory=list); usages:list[Usage]=field(default_factory=list); path:Path|None=None
class Store:
 def __init__(self,root=None):
  self.root=Path(root or Path.home()/'.krbi'/'chats');self.root.mkdir(parents=True,exist_ok=True);self._lock=RLock();self._ids=count(1);self._chats={}
 def new_chat(self,title,provider,model):
  with self._lock:
   cid=next(self._ids);path=self.root/f'chat-{cid:06d}.md';chat=Chat(cid,title,provider,model,path=path);self._chats[cid]=chat
   path.write_text(f'# {title}\n\n- Provider: `{provider}`\n- Model: `{model}`\n- Created: `{datetime.now(timezone.utc).isoformat()}`\n\n---\n');return cid
 def _append(self,chat,text):
  if chat.path:chat.path.open('a').write(text+'\n')
 def add_message(self,chat_id,message):
  with self._lock:
   c=self._chats[chat_id];c.messages.append(message);label=message.role.upper();self._append(c,f'## {label}\n\n{message.content}\n')
 def add_usage(self,chat_id,usage):
  with self._lock:
   c=self._chats[chat_id];c.usages.append(usage);self._append(c,f'## USAGE\n\n- Prompt tokens: {usage.prompt_tokens}\n- Completion tokens: {usage.completion_tokens}\n- Total tokens: {usage.total_tokens}\n')
 def messages(self,chat_id):
  with self._lock:return list(self._chats[chat_id].messages)
 def chats(self):
  with self._lock:return list(self._chats.values())
 def usage(self,chat_id):
  with self._lock:return list(self._chats[chat_id].usages)
 def delete(self,chat_id):
  with self._lock:
   c=self._chats.pop(chat_id,None)
   if c and c.path and c.path.exists():c.path.unlink()
 def export(self,chat_id):
  c=self._chats[chat_id];return c.path.read_text() if c.path else ''
