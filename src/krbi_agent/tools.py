from __future__ import annotations
import asyncio,datetime,os,platform,subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any,Awaitable,Callable
from .core import ToolCall
ToolFunc=Callable[[dict[str,Any]],Awaitable[Any]|Any]
@dataclass(slots=True)
class ToolSpec:
 name:str;description:str;schema:dict[str,Any];func:ToolFunc;dangerous:bool=False
class ToolRegistry:
 def __init__(self):self._tools={}
 def register(self,t):self._tools[t.name]=t;return t
 def get(self,n):return self._tools[n]
 def list(self):return list(self._tools.values())
 async def call(self,n,args,allow_dangerous=False):
  t=self.get(n)
  if t.dangerous and not allow_dangerous:raise PermissionError(f"tool '{n}' requires approval")
  r=t.func(args);return await r if asyncio.iscoroutine(r) else r
 def schemas(self):return [{"type":"function","function":{"name":t.name,"description":t.description,"parameters":t.schema}} for t in self.list()]
def default_tools(root:Path|None=None):
 r=ToolRegistry();root=(root or Path.cwd()).resolve()
 def safe_path(p):
  q=Path(p).expanduser();q=(root/q).resolve() if not q.is_absolute() else q.resolve()
  if root not in q.parents and q!=root:raise PermissionError(f"path outside workspace: {q}")
  return q
 r.register(ToolSpec("clock","Get current local and UTC time.",{"type":"object","properties":{}},lambda a:{"local":datetime.datetime.now().astimezone().isoformat(),"utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}))
 r.register(ToolSpec("system_info","Get runtime platform information.",{"type":"object","properties":{}},lambda a:{"platform":platform.platform(),"python":platform.python_version(),"cwd":os.getcwd()}))
 async def read_file(a):p=safe_path(a["path"]);return {"path":str(p),"content":p.read_text(errors="replace")}
 r.register(ToolSpec("read_file","Read a UTF-8 text file in the workspace.",{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]},read_file))
 async def list_dir(a):p=safe_path(a.get("path","."));return {"path":str(p),"entries":sorted(x.name for x in p.iterdir())}
 r.register(ToolSpec("list_dir","List entries in a workspace directory.",{"type":"object","properties":{"path":{"type":"string"}}},list_dir))
 async def search_files(a):
  base=safe_path(a.get("path",".")); pattern=str(a.get("pattern","")); needle_text=str(a.get("query","")); max_results=min(int(a.get("max_results",50)),200)
  matches=[]
  for item in base.rglob(pattern or "*"):
   if not item.is_file() or ".git" in item.parts:
    continue
   if needle_text:
    try:
     if needle_text.lower() not in item.read_text(errors="replace").lower():
      continue
    except OSError:
     continue
   matches.append(str(item.relative_to(root)))
   if len(matches)>=max_results:
    break
  return {"path":str(base),"query":needle_text,"pattern":pattern or "*","matches":matches,"truncated":len(matches)>=max_results}
 r.register(ToolSpec("search_files","Find workspace files, optionally filtering file contents; read-only.",{"type":"object","properties":{"path":{"type":"string"},"pattern":{"type":"string"},"query":{"type":"string"},"max_results":{"type":"integer"}}},search_files))
 async def file_exists(a):
  p=safe_path(a["path"]); return {"path":str(p),"exists":p.exists(),"is_file":p.is_file(),"is_dir":p.is_dir()}
 r.register(ToolSpec("file_exists","Check whether a workspace path exists.",{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]},file_exists))
 async def write_file(a):p=safe_path(a["path"]);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(a.get("content",""));return {"ok":True,"path":str(p)}
 r.register(ToolSpec("write_file","Write text to a workspace file; requires explicit approval.",{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]},write_file,True))
 async def shell(a):
  cp=subprocess.run(a["command"],shell=True,capture_output=True,text=True,timeout=min(int(a.get("timeout",20)),60),cwd=str(root));return {"returncode":cp.returncode,"stdout":cp.stdout[-12000:],"stderr":cp.stderr[-12000:]}
 r.register(ToolSpec("shell","Run a shell command in the workspace; requires explicit approval.",{"type":"object","properties":{"command":{"type":"string"},"timeout":{"type":"integer"}},"required":["command"]},shell,True))
 return r
class ToolExecutor:
 def __init__(self,registry=None,root=None):self.registry=registry or default_tools(root)
 def schemas(self):return self.registry.schemas()
 async def call(self,call,args=None,allow_dangerous=False):
  if isinstance(call,ToolCall):return await self.registry.call(call.name,call.arguments,allow_dangerous)
  return await self.registry.call(call,args or {},allow_dangerous)
