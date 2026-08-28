import asyncio
from krbi_agent.tools import ToolExecutor

def test_safe_and_dangerous_tools():
 async def run():
  x=ToolExecutor(); r=await x.call('clock',{}); assert 'T' in r['utc']
  try: await x.call('shell',{'command':'echo blocked'})
  except PermissionError: pass
  else: raise AssertionError('dangerous tool was not blocked')
 asyncio.run(run())

def test_search_and_exists_tools():
 async def run():
  x=ToolExecutor()
  result=await x.call('file_exists',{'path':'README.md'})
  assert result['exists'] is True and result['is_file'] is True
  found=await x.call('search_files',{'pattern':'README.md','query':'KRBI','max_results':5})
  assert any(path.endswith('README.md') for path in found['matches'])
 asyncio.run(run())


def test_normalize_models_deduplicates_and_ranks_openrouter_free():
 from krbi_agent.providers import normalize_models
 from krbi_agent.core import ModelInfo
 models=[ModelInfo("openrouter","paid"),ModelInfo("openrouter","demo:free"),ModelInfo("openrouter","paid"),ModelInfo("openrouter","openrouter/free")]
 ranked=normalize_models("openrouter",models)
 assert [m.id for m in ranked] == ["demo:free","openrouter/free","paid"]
