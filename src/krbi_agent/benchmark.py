from __future__ import annotations
import time
from dataclasses import dataclass
from .core import ChatMessage
@dataclass(slots=True)
class BenchmarkResult:
    provider:str; model:str; ok:bool; seconds:float; chars:int=0; error:str=''
async def benchmark_one(registry,provider,model,prompt='Say hello in one sentence.'):
    start=time.perf_counter(); chars=0
    try:
        async for e in registry.get(provider).stream_chat([ChatMessage('user',prompt)],model):
            if e.type=='delta': chars+=len(e.delta)
        return BenchmarkResult(provider,model,True,time.perf_counter()-start,chars)
    except Exception as e:return BenchmarkResult(provider,model,False,time.perf_counter()-start,chars,str(e))
async def compare(registry,candidates,prompt='Say hello in one sentence.'):
    out=[]
    for provider,model in candidates: out.append(await benchmark_one(registry,provider,model,prompt))
    return sorted(out,key=lambda x:(not x.ok,x.seconds))
