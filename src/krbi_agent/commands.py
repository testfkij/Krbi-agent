from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True,slots=True)
class Command:
 name:str; description:str; action:str
COMMANDS=[
 Command('/help','Show commands','help'),Command('/goal','Set or show the current agent goal','goal'),Command('/system','Set system prompt','system'),
 Command('/provider','Select a provider','provider'),Command('/model','Select a model','model'),Command('/local','Show or use local model providers','local'),Command('/providers','List providers','providers'),Command('/models','Refresh/search models','models'),
 Command('/tools','List available tools','tools'),Command('/approve','Approve a tool for future calls','approve'),Command('/revoke','Revoke a tool approval','revoke'),
 Command('/approval','Set tool approval mode','approval'),Command('/settings','Open KRBI settings','settings'),Command('/mcp','Inspect MCP tools','mcp'),
 Command('/benchmark','Benchmark models','benchmark'),Command('/banner','Set or show the UI banner','banner'),Command('/new','Start a new chat','new'),
 Command('/clear','Clear transcript','clear'),Command('/reset','Reset the current session','reset'),Command('/history','Show chat history','history'),Command('/tokens','Show token usage','tokens'),Command('/export','Export current chat','export'),Command('/quit','Exit KRBI Agent','quit')]
def search_commands(q):
 q=q.lower().lstrip('/'); return [c for c in COMMANDS if q in c.name.lower() or q in c.description.lower()]
