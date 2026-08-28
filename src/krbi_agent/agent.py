from __future__ import annotations
import json
from typing import AsyncIterator
from .core import ChatMessage, StreamEvent, Usage, ToolCall
from .providers import ProviderRegistry
from .storage import Store
from .tools import ToolExecutor
from .settings import Settings, load_settings
DEFAULT_SYSTEM='You are KRBI Agent, a capable general-purpose AI agent. Be accurate, useful, safe, and transparent about uncertainty.'
class Agent:
 def __init__(self,registry=None,store=None,tools=None,settings:Settings|None=None):
  self.registry=registry or ProviderRegistry(); self.store=store or Store(); self.settings=settings or load_settings(); self.tools=tools or ToolExecutor()
 def _tool_defs(self): return self.tools.schemas()
 async def run(self,chat_id,provider,model,prompt,system_prompt=None,goal=None,allow_dangerous=False,api_key=None,max_tool_rounds=8,**params)->AsyncIterator[StreamEvent]:
  history=self.store.messages(chat_id); sys=system_prompt or DEFAULT_SYSTEM
  if goal: sys+=f'\n\nCurrent user goal:\n{goal}'
  messages=[ChatMessage('system',sys),*history,ChatMessage('user',prompt)]; self.store.add_message(chat_id,ChatMessage('user',prompt)); final_parts=[]; last_usage=Usage()
  params=dict(params); params.setdefault('tools',self._tool_defs())
  for _ in range(max_tool_rounds):
   parts=[]; tool_acc={}; round_usage=Usage(); saw_tool=False
   try:
    async for ev in self.registry.get(provider,api_key=api_key).stream_chat(messages,model,**params):
     if ev.type=='delta': parts.append(ev.delta); yield ev
     elif ev.type=='usage': round_usage=ev.usage or round_usage; last_usage=round_usage; yield ev
     elif ev.type=='tool_call_delta':
      saw_tool=True
      for c in ev.tool_calls:
       idx=c.get('index',0); cur=tool_acc.setdefault(idx,{'id':c.get('id') or f'tool_{idx}','name':None,'arguments':''})
       if c.get('id'):cur['id']=c['id']
       fn=c.get('function') or {}
       if fn.get('name'):cur['name']=fn['name']
       if fn.get('arguments'):cur['arguments']+=fn['arguments']
   except Exception as e:
    yield StreamEvent('error',message=str(e)); return
   text=''.join(parts); final_parts.append(text)
   if not saw_tool:
    answer=''.join(final_parts); self.store.add_message(chat_id,ChatMessage('assistant',answer))
    if last_usage.total_tokens:self.store.add_usage(chat_id,last_usage)
    yield StreamEvent('done'); return
   calls=[]
   for c in tool_acc.values():
    try: args=json.loads(c['arguments'] or '{}')
    except json.JSONDecodeError as e: args={'_raw':c['arguments'],'_parse_error':str(e)}
    calls.append(ToolCall(c['id'],c['name'] or 'unknown',args))
   assistant_call_docs=[{'id':c.id,'type':'function','function':{'name':c.name,'arguments':json.dumps(c.arguments)}} for c in calls]
   messages.append(ChatMessage('assistant',text,tool_calls=assistant_call_docs))
   for call in calls:
    try:
     spec=self.tools.registry.get(call.name); approved=allow_dangerous or self.settings.tool_allowed(call.name,spec.dangerous)
     yield StreamEvent('tool_start',message=call.name,raw={'tool_call':call.id})
     if spec.dangerous and not approved: raise PermissionError(f"tool '{call.name}' is not approved; use /approve {call.name}")
     result=await self.tools.call(call,approved)
    except Exception as e: result={'error':str(e)}
    yield StreamEvent('tool_result',message=call.name,raw={'tool_call':call.id,'result':result})
    messages.append(ChatMessage('tool',json.dumps(result,default=str),name=call.name,tool_call_id=call.id))
  yield StreamEvent('error',message=f'Agent stopped after {max_tool_rounds} tool rounds')
