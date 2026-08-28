from __future__ import annotations

import argparse
import asyncio
import getpass

from rich.console import Console
from rich.table import Table

from .agent import Agent, DEFAULT_SYSTEM
from .config import load_configs
from .providers import ProviderRegistry
from .storage import Store
from .ui import pick
from .settings import Settings, save_settings, SETTINGS_PATH
from .updater import check_for_update, current_info, update_and_restart, reinstall_checkout

console = Console()


def reg() -> ProviderRegistry:
    return ProviderRegistry(load_configs())


async def discover(registry: ProviderRegistry, provider: str, api_key: str | None = None):
    return await registry.get(provider, api_key=api_key or None).list_models()


async def do_models(registry: ProviderRegistry) -> None:
    table = Table(title="KRBI Agent · Live Models")
    table.add_column("Provider")
    table.add_column("Model")
    table.add_column("Capabilities")
    for name in registry.names():
        try:
            models = await discover(registry, name)
        except Exception as exc:
            table.add_row(name, "—", f"error: {str(exc)[:70]}")
            continue
        for model in models:
            table.add_row(name, model.id, ", ".join(sorted(model.capabilities)))
    console.print(table)


def chat(registry: ProviderRegistry) -> None:
    choices = list(registry.names())
    provider = pick("Choose provider — ↑/↓, Enter", choices)
    configured = registry.configs[provider]
    api_key = getpass.getpass(f"API key for {provider} (empty uses environment/config): ").strip()
    try:
        models = asyncio.run(discover(registry, provider, api_key))
    except Exception as exc:
        console.print(f"[red]Model discovery failed:[/] {exc}")
        return
    if not models:
        console.print("[yellow]No models were returned by the provider.[/]")
        return
    model = pick("Choose live model — ↑/↓, Enter", [m.id for m in models])
    store = Store()
    agent = Agent(registry, store)
    chat_id = store.new_chat("KRBI CLI chat", provider, model)
    system = DEFAULT_SYSTEM
    goal = ""
    console.print(f"[bold]KRBI Agent[/] · {provider}/{model} · /goal /system /tools /approval /quit")
    if configured.models and not api_key:
        console.print("[dim]Using configured/env discovery rules; provide a key to request the provider's live model catalog.[/]")
    while True:
        try:
            prompt = console.input("[cyan]you[/] › ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if prompt in {"/exit", "/quit"}:
            break
        if prompt.startswith("/goal "):
            goal = prompt[6:].strip(); console.print(f"goal={goal}"); continue
        if prompt.startswith("/system "):
            system = prompt[8:].strip() or DEFAULT_SYSTEM; console.print("system prompt updated"); continue
        if prompt == "/providers":
            console.print("\n".join(registry.names())); continue
        if prompt == "/models":
            try:
                models = asyncio.run(discover(registry, provider, api_key))
                console.print("\n".join(m.id for m in models) or "No models returned")
            except Exception as exc: console.print(f"[red]{exc}[/]")
            continue
        if prompt == "/tools":
            from .tools import default_tools
            console.print(", ".join(t.name for t in default_tools().list())); continue
        if prompt == "/settings":
            console.print("Settings are persisted in ~/.krbi/settings.toml"); continue
        if prompt.startswith("/approval "):
            agent.settings.approval_mode = prompt.split(" ", 1)[1].strip(); console.print(f"approval={agent.settings.approval_mode}"); continue
        if not prompt: continue
        console.print("[green]krbi[/] › ", end="")

        async def run_once() -> None:
            async for event in agent.run(chat_id, provider, model, prompt, system_prompt=system, goal=goal, api_key=api_key or None):
                if event.type == "delta": console.print(event.delta, end="")
                elif event.type == "tool_result": pass
                elif event.type == "error": console.print(f"\n[red]{event.message}[/]", end="")
            console.print()

        asyncio.run(run_once())


def main() -> None:
    parser = argparse.ArgumentParser(prog="krbi", description="KRBI Agent · free and open source")
    parser.add_argument("--version", action="store_true", help="Show the current KRBI version marker")
    parser.add_argument("--no-update-check", action="store_true", help="Skip the startup GitHub update check")
    parser.add_argument("--reinstall", action="store_true", help="Reinstall KRBI from GitHub main and restart")
    parser.add_argument("--banner", metavar="TEXT", help="Custom launch banner")
    subs = parser.add_subparsers(dest="cmd")
    for name in ("providers", "models", "chat", "tui", "run", "config-example", "mcp", "benchmark", "reset", "update"):
        subs.add_parser(name)
    web = subs.add_parser("web", help="Run the browser UI")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    info = current_info()
    if args.version:
        console.print(f"KRBI Agent v{info.version} · type {info.version_type} · code {info.code}")
        return
    if args.reinstall:
        reinstall_checkout()
        return
    if args.cmd is None:
        parser.print_help()
        return
    banner = args.banner.strip() if args.banner else "KRBI // AGENT"
    console.print(f"[bold cyan]{banner}[/] [dim]v{info.version} · {info.version_type} · code {info.code}[/]")
    if not args.no_update_check and args.cmd != "update":
        local, remote = check_for_update()
        if remote and remote.code > local.code:
            console.print(f"[yellow]Update available:[/] v{remote.version} · {remote.version_type} · code {remote.code}. Updating and restarting…")
            update_and_restart([a for a in __import__('sys').argv[1:] if a != "--no-update-check"])
    registry = reg()
    if args.cmd == "providers":
        for name in registry.names(): console.print(f"• {name} [{registry.configs[name].kind}]")
    elif args.cmd == "models": asyncio.run(do_models(registry))
    elif args.cmd == "chat": chat(registry)
    elif args.cmd in {"tui", "run"}:
        from .textual_app import run; run()
    elif args.cmd == "config-example":
        from .config import save_example; save_example(); console.print("wrote ~/.krbi/config.toml")
    elif args.cmd == "mcp":
        from .mcp import MCPServer
        for tool in MCPServer().tools_list(): console.print(f"• {tool['function']['name']} — {tool['function']['description']}")
    elif args.cmd in {"benchmark"}:
        async def run_bench() -> None:
            from .benchmark import compare
            pairs = [(n, cfg.models[0]) for n, cfg in registry.configs.items() if cfg.models]
            for result in await compare(registry, pairs[:12]):
                console.print(f"{result.provider}/{result.model}: {'OK' if result.ok else 'FAIL'} {result.seconds:.2f}s {result.chars} chars {result.error}")
        asyncio.run(run_bench())
    elif args.cmd == "reset":
        save_settings(Settings(), SETTINGS_PATH)
        console.print(f"Reset KRBI settings at {SETTINGS_PATH}. Saved chats were preserved.")
    elif args.cmd == "update":
        console.print("[dim]Checking GitHub for updates…[/]")
        local, remote = check_for_update(force=True)
        if remote is None:
            console.print(f"GitHub update check unavailable. Current: v{local.version} · code {local.code}")
        elif remote.code <= local.code:
            console.print(f"Already current: v{local.version} · {local.version_type} · code {local.code}")
        else:
            update_and_restart(["run"])
    elif args.cmd == "web":
        from .web import serve; serve(args.host, args.port)


if __name__ == "__main__":
    main()
