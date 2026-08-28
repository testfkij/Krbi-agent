import asyncio,tempfile
from krbi_agent.agent import Agent
from krbi_agent.core import StreamEvent
from krbi_agent.storage import Store
class FakeProvider:
 def __init__(self):self.n=0
 async def stream_chat(self,messages,model,**kwargs):
  self.n+=1
  if self.n==1:
   assert kwargs.get('tools');yield StreamEvent('tool_call_delta',tool_calls=[{'index':0,'id':'c1','type':'function','function':{'name':'clock','arguments':'{}'}}]);yield StreamEvent('done')
  else:
   assert any(m.role=='tool' for m in messages);yield StreamEvent('delta',delta='Done.');yield StreamEvent('done')
class Reg:
 def __init__(self):self.p=FakeProvider()
 def get(self,name,api_key=None):return self.p
async def run():
 with tempfile.TemporaryDirectory() as d:
  s=Store(d);cid=s.new_chat('t','fake','m');events=[]
  async for e in Agent(Reg(),s).run(cid,'fake','m','what time?',allow_dangerous=False):events.append(e)
  assert any(e.type=='tool_result' for e in events);assert s.messages(cid)[-1].content=='Done.'
def test_agent_tool_loop():asyncio.run(run())
