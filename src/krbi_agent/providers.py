from __future__ import annotations
import json,os
from dataclasses import dataclass,field
from typing import AsyncIterator
import httpx
from .core import ChatMessage,ModelInfo,StreamEvent,Usage
@dataclass(slots=True)
class ProviderConfig:
 name:str;kind:str='openai-compatible';base_url:str='https://api.openai.com/v1';api_key_env:str|None=None;models:list[str]=field(default_factory=list);headers:dict[str,str]=field(default_factory=dict);model_url:str|None=None;api_version:str|None=None
PROVIDER_DEFAULTS={'openai':ProviderConfig('openai',base_url='https://api.openai.com/v1',api_key_env='OPENAI_API_KEY'),'azure-openai':ProviderConfig('azure-openai',kind='azure-openai',api_key_env='AZURE_OPENAI_API_KEY'),'openrouter':ProviderConfig('openrouter',base_url='https://openrouter.ai/api/v1',api_key_env='OPENROUTER_API_KEY'),'groq':ProviderConfig('groq',base_url='https://api.groq.com/openai/v1',api_key_env='GROQ_API_KEY'),'mistral':ProviderConfig('mistral',base_url='https://api.mistral.ai/v1',api_key_env='MISTRAL_API_KEY'),'deepseek':ProviderConfig('deepseek',base_url='https://api.deepseek.com/v1',api_key_env='DEEPSEEK_API_KEY'),'together':ProviderConfig('together',base_url='https://api.together.xyz/v1',api_key_env='TOGETHER_API_KEY'),'fireworks':ProviderConfig('fireworks',base_url='https://api.fireworks.ai/inference/v1',api_key_env='FIREWORKS_API_KEY'),'xai':ProviderConfig('xai',base_url='https://api.x.ai/v1',api_key_env='XAI_API_KEY'),'cohere':ProviderConfig('cohere',base_url='https://api.cohere.com/compatibility/v1',api_key_env='COHERE_API_KEY'),'ollama':ProviderConfig('ollama',base_url='http://127.0.0.1:11434/v1'),
'lm-studio':ProviderConfig('lm-studio',base_url='http://127.0.0.1:1234/v1'),
'llama-cpp':ProviderConfig('llama-cpp',base_url='http://127.0.0.1:8080/v1'),
'vllm-local':ProviderConfig('vllm-local',base_url='http://127.0.0.1:8000/v1'),'google':ProviderConfig('google',kind='gemini-native',base_url='https://generativelanguage.googleapis.com/v1beta',api_key_env='GOOGLE_API_KEY'),'anthropic':ProviderConfig('anthropic',kind='anthropic',base_url='https://api.anthropic.com/v1',api_key_env='ANTHROPIC_API_KEY')}
class BaseHTTPProvider:
 def __init__(self,config,timeout=180,api_key=None):self.config,self.name,self.timeout,self.runtime_api_key=config,config.name,timeout,api_key
 def _api_key(self):return self.runtime_api_key or (os.getenv(self.config.api_key_env) if self.config.api_key_env else None)
class OpenAICompatibleProvider(BaseHTTPProvider):
 def _headers(self):
  h={'content-type':'application/json',**self.config.headers}
  if k:=self._api_key():h['authorization']=f'Bearer {k}'
  return h
 async def list_models(self):
  if self.config.models and not self._api_key() and self.name != 'ollama': return [ModelInfo(self.name,m,m,capabilities={'chat','streaming','tools'}) for m in self.config.models]
  async with httpx.AsyncClient(timeout=self.timeout) as c:r=await c.get(self.config.model_url or f"{self.config.base_url.rstrip('/')}/models",headers=self._headers());r.raise_for_status();d=r.json()
  return [ModelInfo(self.name,x['id'],x.get('id'),capabilities={'chat','streaming','tools'}) for x in d.get('data',[]) if x.get('id')]
 async def stream_chat(self,messages,model,**kwargs):
  def wire(m):
   x={'role':m.role,'content':m.content}
   if m.name:x['name']=m.name
   if m.tool_call_id:x['tool_call_id']=m.tool_call_id
   if m.tool_calls:x['tool_calls']=m.tool_calls
   return x
  p={'model':model,'messages':[wire(m) for m in messages],'stream':True,**kwargs}
  async with httpx.AsyncClient(timeout=self.timeout) as c:
   async with c.stream('POST',f"{self.config.base_url.rstrip('/')}/chat/completions",headers=self._headers(),json=p) as r:
    if r.status_code>=400:b=await r.aread();raise RuntimeError(f"{self.name} HTTP {r.status_code}: {b.decode(errors='replace')[:1500]}")
    async for line in r.aiter_lines():
     if not line or not line.startswith('data:'):continue
     raw=line[5:].strip()
     if raw=='[DONE]':yield StreamEvent('done');return
     try:o=json.loads(raw)
     except json.JSONDecodeError:continue
     ch=o.get('choices') or []
     if ch:
      d=ch[0].get('delta') or {};text=d.get('content') or ''
      if text:yield StreamEvent('delta',delta=text,raw=o)
      if d.get('tool_calls'):yield StreamEvent('tool_call_delta',tool_calls=d['tool_calls'],raw=o)
     if u:=o.get('usage'):yield StreamEvent('usage',usage=Usage(u.get('prompt_tokens',0),u.get('completion_tokens',0),u.get('total_tokens',0)),raw=o)
class AnthropicProvider(BaseHTTPProvider):
 def _headers(self):return {'content-type':'application/json','x-api-key':self._api_key() or '','anthropic-version':'2023-06-01',**self.config.headers}
 async def list_models(self):
  if self.config.models and not self._api_key() and self.name != 'ollama': return [ModelInfo(self.name,m,m,capabilities={'chat','streaming','tools'}) for m in self.config.models]
  async with httpx.AsyncClient(timeout=self.timeout) as c:r=await c.get(f"{self.config.base_url.rstrip('/')}/models",headers=self._headers());r.raise_for_status();d=r.json()
  return [ModelInfo(self.name,x['id'],x.get('display_name') or x['id'],capabilities={'chat','streaming','tools'}) for x in d.get('data',[]) if x.get('id')]
 async def stream_chat(self,messages,model,**kwargs):
  systems=[m.content for m in messages if m.role=='system'];items=[]
  for m in messages:
   if m.role=='system':continue
   if m.role=='tool':items.append({'role':'user','content':[{'type':'tool_result','tool_use_id':m.tool_call_id or '','content':m.content}]})
   elif m.tool_calls:items.append({'role':'assistant','content':[{'type':'tool_use','id':x['id'],'name':x['function']['name'],'input':json.loads(x['function'].get('arguments') or '{}')} for x in m.tool_calls]})
   else:items.append({'role':m.role,'content':m.content})
  p={'model':model,'max_tokens':kwargs.pop('max_tokens',4096),'stream':True,'messages':items,**kwargs}
  if systems:p['system']='\n\n'.join(systems)
  if tools:=p.get('tools'):p['tools']=[{'name':t['function']['name'],'description':t['function']['description'],'input_schema':t['function']['parameters']} for t in tools]
  async with httpx.AsyncClient(timeout=self.timeout) as c:
   async with c.stream('POST',f"{self.config.base_url.rstrip('/')}/messages",headers=self._headers(),json=p) as r:
    if r.status_code>=400:b=await r.aread();raise RuntimeError(f"{self.name} HTTP {r.status_code}: {b.decode(errors='replace')[:1500]}")
    async for line in r.aiter_lines():
     if not line.startswith('data:'):continue
     try:o=json.loads(line[5:].strip())
     except json.JSONDecodeError:continue
     typ=o.get('type');delta=o.get('delta') or {}
     if typ=='content_block_delta' and delta.get('type')=='text_delta' and delta.get('text'):yield StreamEvent('delta',delta=delta['text'],raw=o)
     elif typ=='content_block_start' and (b:=o.get('content_block',{})).get('type')=='tool_use':yield StreamEvent('tool_call_delta',tool_calls=[{'index':o.get('index',0),'id':b.get('id'),'type':'function','function':{'name':b.get('name'),'arguments':''}}],raw=o)
     elif typ=='content_block_delta' and delta.get('type')=='input_json_delta':yield StreamEvent('tool_call_delta',tool_calls=[{'index':o.get('index',0),'function':{'arguments':delta.get('partial_json','')}}],raw=o)
     elif typ=='message_stop':yield StreamEvent('done')
class GeminiNativeProvider(BaseHTTPProvider):
 async def list_models(self):
  if self.config.models and not self._api_key(): return [ModelInfo(self.name,m,m,capabilities={'chat','streaming','tools'}) for m in self.config.models]
  async with httpx.AsyncClient(timeout=self.timeout) as c:r=await c.get(f"{self.config.base_url.rstrip('/')}/models?key={self._api_key() or ''}");r.raise_for_status();d=r.json()
  return [ModelInfo(self.name,x['name'].split('models/')[-1],x.get('displayName'),capabilities={'chat','streaming','tools'}) for x in d.get('models',[]) if 'generateContent' in x.get('supportedGenerationMethods',[])]
 async def stream_chat(self,messages,model,**kwargs):
  sys=[m.content for m in messages if m.role=='system'];contents=[]
  for m in messages:
   if m.role=='system':continue
   role='model' if m.role=='assistant' else 'user';parts=[{'text':m.content}] if m.content else []
   if m.tool_calls:parts=[{'functionCall':{'name':x['function']['name'],'args':json.loads(x['function'].get('arguments') or '{}')}} for x in m.tool_calls]
   if m.role=='tool':parts=[{'functionResponse':{'name':m.name or 'tool','response':{'result':m.content}}}]
   contents.append({'role':role,'parts':parts})
  p={'contents':contents,'generationConfig':{k:v for k,v in kwargs.items() if k not in ('tools','max_tokens')}}
  if sys:p['systemInstruction']={'parts':[{'text':'\n\n'.join(sys)}]}
  if tools:=kwargs.get('tools'):p['tools']=[{'function_declarations':[{'name':t['function']['name'],'description':t['function']['description'],'parameters':t['function']['parameters']} for t in tools]}]
  url=f"{self.config.base_url.rstrip('/')}/models/{model}:streamGenerateContent?alt=sse&key={self._api_key() or ''}"
  async with httpx.AsyncClient(timeout=self.timeout) as c:
   async with c.stream('POST',url,headers={'content-type':'application/json'},json=p) as r:
    if r.status_code>=400:b=await r.aread();raise RuntimeError(f"{self.name} HTTP {r.status_code}: {b.decode(errors='replace')[:1500]}")
    async for line in r.aiter_lines():
     if not line.startswith('data:'):continue
     try:o=json.loads(line[5:].strip())
     except json.JSONDecodeError:continue
     for part in (((o.get('candidates') or [{}])[0].get('content') or {}).get('parts') or []):
      if part.get('text'):yield StreamEvent('delta',delta=part['text'],raw=o)
      if f:=part.get('functionCall'):yield StreamEvent('tool_call_delta',tool_calls=[{'index':0,'id':f.get('name'),'type':'function','function':{'name':f.get('name'),'arguments':json.dumps(f.get('args',{}))}}],raw=o)
    yield StreamEvent('done')
class AzureOpenAIProvider(OpenAICompatibleProvider):
 def _headers(self):return {'content-type':'application/json','api-key':self._api_key() or '',**self.config.headers}
 async def list_models(self):
  if self.config.models and not self._api_key(): return [ModelInfo(self.name,m,m,capabilities={'chat','streaming','tools'}) for m in self.config.models]
  v=self.config.api_version or os.getenv('AZURE_OPENAI_API_VERSION','2024-10-21')
  async with httpx.AsyncClient(timeout=self.timeout) as c:
   r=await c.get(f"{self.config.base_url.rstrip('/')} /openai/models?api-version={v}".replace(' ',''),headers=self._headers()); r.raise_for_status(); d=r.json()
  return [ModelInfo(self.name,x['id'],x.get('id'),capabilities={'chat','streaming','tools'}) for x in d.get('data',[]) if x.get('id') and x.get('capabilities',{}).get('inference',True)]
 async def stream_chat(self,messages,model,**kwargs):
  v=self.config.api_version or os.getenv('AZURE_OPENAI_API_VERSION','2024-10-21');url=f"{self.config.base_url.rstrip('/')}/openai/deployments/{model}/chat/completions?api-version={v}"
  def wire(m):
   x={'role':m.role,'content':m.content}
   if m.tool_call_id:x['tool_call_id']=m.tool_call_id
   if m.tool_calls:x['tool_calls']=m.tool_calls
   return x
  p={'messages':[wire(m) for m in messages],'stream':True,**kwargs}
  async with httpx.AsyncClient(timeout=self.timeout) as c:
   async with c.stream('POST',url,headers=self._headers(),json=p) as r:
    if r.status_code>=400:b=await r.aread();raise RuntimeError(f"{self.name} HTTP {r.status_code}: {b.decode(errors='replace')[:1500]}")
    async for line in r.aiter_lines():
     if not line or not line.startswith('data:'):continue
     raw=line[5:].strip()
     if raw=='[DONE]':yield StreamEvent('done');return
     try:o=json.loads(raw)
     except json.JSONDecodeError:continue
     ch=o.get('choices') or []
     if ch:
      d=ch[0].get('delta') or {}
      if d.get('content'):yield StreamEvent('delta',delta=d['content'],raw=o)
      if d.get('tool_calls'):yield StreamEvent('tool_call_delta',tool_calls=d['tool_calls'],raw=o)
class ProviderRegistry:
 def __init__(self,configs=None):self.configs={**PROVIDER_DEFAULTS,**(configs or {})}
 def names(self):return list(self.configs)
 def get(self,name,api_key=None):
  cfg=self.configs[name];cls={'anthropic':AnthropicProvider,'gemini-native':GeminiNativeProvider,'azure-openai':AzureOpenAIProvider}.get(cfg.kind,OpenAICompatibleProvider);return cls(cfg,api_key=api_key)
