from __future__ import annotations
import os
import re
from pathlib import Path
from urllib.parse import urlparse
from .providers import ProviderConfig

CONFIG_PATH = Path(os.getenv("KRBI_CONFIG", Path.home() / ".krbi" / "config.toml"))
PROVIDER_NAME = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,48}$")
RESERVED = {"openai", "azure-openai", "openrouter", "groq", "mistral", "anthropic", "gemini", "ollama", "lm-studio", "llama-cpp", "vllm-local"}

def load_configs(path: Path = CONFIG_PATH) -> dict[str, ProviderConfig]:
    if not path.exists():
        return {}
    import tomllib
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    output = {}
    for name, raw in data.get("providers", {}).items():
        output[name] = ProviderConfig(name=name, **{key: value for key, value in raw.items() if key != "name"})
    return output

def save_example(path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('[providers.my-gateway]\nkind = "openai-compatible"\nbase_url = "https://example/v1"\napi_key_env = "MY_API_KEY"\nmodels = ["model-a"]\n\n[providers.my-anthropic]\nkind = "anthropic"\nbase_url = "https://api.anthropic.com/v1"\napi_key_env = "ANTHROPIC_API_KEY"\nmodels = ["claude-sonnet"]\n', encoding="utf-8")

def add_provider(name: str, base_url: str, api_key_env: str = "", model: str = "", path: Path | None = None) -> ProviderConfig:
    name = str(name).strip()
    if not PROVIDER_NAME.fullmatch(name):
        raise ValueError("Provider name must start with a letter and contain only letters, digits, _ or - (max 49 characters).")
    if name.lower() in RESERVED:
        raise ValueError("That name belongs to a built-in provider.")
    url = str(base_url).strip().rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Base URL must be an http(s) URL without embedded credentials.")
    env_name = str(api_key_env).strip()
    if env_name and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", env_name):
        raise ValueError("API-key environment variable name is invalid.")
    model = str(model).strip()
    if len(model) > 240:
        raise ValueError("Model ID is too long.")
    target = path or CONFIG_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = load_configs(target)
    if name in existing:
        raise ValueError(f"Provider already exists: {name}")
    def quote(value: str) -> str:
        return json_quote(value)
    block = (
        f'\n[providers."{name}"]\nkind = "openai-compatible"\n'
        f'base_url = {quote(url)}\napi_key_env = {quote(env_name)}\n'
        + (f'models = [{quote(model)}]\n' if model else 'models = []\n')
    )
    prior = target.read_text(encoding="utf-8") if target.exists() else ""
    target.write_text(prior.rstrip() + "\n" + block, encoding="utf-8")
    return ProviderConfig(name=name, kind="openai-compatible", base_url=url, api_key_env=env_name or None, models=[model] if model else [])

def json_quote(value: str) -> str:
    import json
    return json.dumps(value, ensure_ascii=False)

def remove_provider(name: str, path: Path | None = None) -> bool:
    target = path or CONFIG_PATH
    if name.lower() in RESERVED:
        raise ValueError("Built-in providers cannot be removed.")
    if not target.exists():
        return False
    import tomllib
    data = tomllib.loads(target.read_text(encoding="utf-8"))
    providers = data.get("providers", {})
    if name not in providers:
        return False
    del providers[name]
    lines = []
    for provider_name, cfg in providers.items():
        lines.extend(["", f'[providers."{provider_name}"]'])
        for key, value in cfg.items():
            lines.append(f"{key} = {json_quote(value) if isinstance(value, str) else __import__('json').dumps(value)}")
    target.write_text("\n".join(lines).lstrip() + "\n", encoding="utf-8")
    return True
