from __future__ import annotations
from dataclasses import dataclass,field
from typing import Any,AsyncIterator,Protocol
@dataclass(slots=True)
class ToolCall:
 id:str; name:str; arguments:dict[str,Any]
@dataclass(slots=True)
class ChatMessage:
 role:str; content:str; name:str|None=None; tool_call_id:str|None=None; tool_calls:list[dict[str,Any]]|None=None
@dataclass(slots=True)
class Usage:
 prompt_tokens:int=0; completion_tokens:int=0; total_tokens:int=0
@dataclass(slots=True)
class StreamEvent:
 type:str; delta:str=""; message:str=""; usage:Usage|None=None; tool_calls:list[dict[str,Any]]=field(default_factory=list); raw:dict[str,Any]=field(default_factory=dict)
@dataclass(slots=True)
class ModelInfo:
 provider:str; id:str; name:str|None=None; context_window:int|None=None; capabilities:set[str]=field(default_factory=set)
class Provider(Protocol):
 name:str
 async def list_models(self)->list[ModelInfo]: ...
 async def stream_chat(self,messages:list[ChatMessage],model:str,**kwargs:Any)->AsyncIterator[StreamEvent]: ...
