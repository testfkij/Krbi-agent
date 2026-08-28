from __future__ import annotations

import os
from pathlib import Path
from .providers import ProviderConfig

CONFIG_PATH=Path(os.getenv('KRBI_CONFIG',Path.home()/'.krbi'/'config.toml'))

def load_configs(path:Path=CONFIG_PATH)->dict[str,ProviderConfig]:
    if not path.exists(): return {}
    import tomllib
    data=tomllib.loads(path.read_text())
    out={}
    for name,raw in data.get('providers',{}).items(): out[name]=ProviderConfig(name=name,**{k:v for k,v in raw.items() if k!='name'})
    return out

def save_example(path:Path=CONFIG_PATH)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('[providers.my-gateway]\nkind = "openai-compatible"\nbase_url = "https://example/v1"\napi_key_env = "MY_API_KEY"\nmodels = ["model-a"]\n\n[providers.my-anthropic]\nkind = "anthropic"\nbase_url = "https://api.anthropic.com/v1"\napi_key_env = "ANTHROPIC_API_KEY"\nmodels = ["claude-sonnet"]\n')
