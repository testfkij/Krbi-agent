from __future__ import annotations
import asyncio,json
from dataclasses import dataclass
from .tools import ToolExecutor,ToolRegistry,ToolSpec
class MCPServer:
 def __init__(self,tools=None):self.tools=tools or ToolExecutor()
 def tools_list(self):return self.tools.schemas()
 async def call(self,name,args,allow_dangerous=False):return await self.tools.call(name,args,allow_dangerous)
 async def handle(self,line):
  req=json.loads(line);method=req.get('method');params=req.get('params') or {}
  try:
   if method in ('initialize',): result={'protocolVersion':'2025-06-18','capabilities':{'tools':{}},'serverInfo':{'name':'krbi-agent','version':'0.4.0'}}
   elif method in ('tools/list','list_tools'):result={'tools':self.tools_list()}
   elif method in ('tools/call','call_tool'):
    result={'content':[{'type':'text','text':json.dumps(await self.call(params['name'],params.get('arguments',{}),bool(params.get('allow_dangerous',False))),default=str)}]}
   else:return {'jsonrpc':'2.0','id':req.get('id'),'error':{'code':-32601,'message':'method not found'}}
   return {'jsonrpc':'2.0','id':req.get('id'),'result':result}
  except Exception as e:return {'jsonrpc':'2.0','id':req.get('id'),'error':{'code':-32000,'message':str(e)}}
@dataclass(slots=True)
class MCPStdioClient:
 command:list[str]
 env:dict[str,str]|None=None
 cwd:str|None=None
 async def request(self,method,params=None):
  proc=await asyncio.create_subprocess_exec(*self.command,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,env=self.env,cwd=self.cwd)
  req={'jsonrpc':'2.0','id':1,'method':method,'params':params or {}}
  proc.stdin.write((json.dumps(req)+'\n').encode());await proc.stdin.drain()
  line=await asyncio.wait_for(proc.stdout.readline(),30);await proc.wait()
  if not line: raise RuntimeError('MCP server closed stdout without a response')
  out=json.loads(line)
  if 'error' in out: raise RuntimeError(out['error'].get('message','MCP error'))
  return out.get('result')
 async def list_tools(self):return (await self.request('tools/list')).get('tools',[])
 async def call_tool(self,name,arguments=None):return await self.request('tools/call',{'name':name,'arguments':arguments or {}})
async def mount_mcp_stdio(registry:ToolRegistry,client:MCPStdioClient,prefix='mcp'):
 for schema in await client.list_tools():
  fn=schema.get('function',schema);name=fn.get('name');desc=fn.get('description','MCP tool');params=fn.get('parameters',{})
  async def invoke(args,n=name):return await client.call_tool(n,args)
  registry.register(ToolSpec(f'{prefix}.{name}',desc,params,invoke,False))
 return registry
