from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from rich.console import Console
from rich.table import Table

from .agent import Agent, DEFAULT_SYSTEM
from .config import load_configs
from .providers import ProviderRegistry
from .storage import Store
from .ui import pick
from .settings import Settings, save_settings, load_settings, SETTINGS_PATH, ensure_mcp_token
from .updater import check_for_update, current_info, update_and_restart, reinstall_checkout, available_versions, install_version, UpdateError
from .tunnel import TunnelManager, PROVIDERS
from .mcp_http import connection_info

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
            table.add_row(name, model.id, ", ".join(sorted(model.capabilities)) or "chat")
    console.print(table)


def doctor() -> int:
    from .doctor import run_checks
    table = Table(title="KRBI Agent · Doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    checks = run_checks()
    for item in checks:
        table.add_row(item.name, "OK" if item.ok else "WARN", item.detail)
    console.print(table)
    return 0 if all(item.ok for item in checks[:4]) else 1


def show_versions() -> None:
    try:
        versions = available_versions()
    except Exception as exc:
        console.print(f"[red]Version index unavailable:[/] {exc}")
        return
    table = Table(title="KRBI Agent · Available Versions (commit based)")
    for col in ("Version", "Type", "Code", "Source"):
        table.add_column(col)
    for item in versions:
        table.add_row(str(item["version"]), str(item.get("version_type", "—")), str(item.get("code", "—")), "current checkout" if item.get("current") else str(item.get("commit", "GitHub")))
    console.print(table)


def mcp_info(client: str = "all") -> None:
    settings = load_settings()
    ensure_mcp_token(settings)
    save_settings(settings)
    status = TunnelManager().status()
    base = status["url"] if status.get("url") else f"http://127.0.0.1:{settings.tunnel_port}"
    info = connection_info(str(base), settings)
    console.print("[bold]KRBI MCP connection[/]")
    console.print(f"Endpoint: {info['endpoint']}")
    console.print(f"Protocol: {info['protocol']}")
    console.print(f"Authorization: {info['authorization']}")
    if client in ("all", "codex"):
        console.print("\n[bold]Codex[/]")
        console.print(f'[mcp_servers.krbi]\nurl = "{info["endpoint"]}"\nbearer_token_env_var = "KRBI_MCP_TOKEN"')
        console.print("Set KRBI_MCP_TOKEN to the bearer token before starting Codex.")
    if client in ("all", "claude"):
        console.print("\n[bold]Claude Code[/]")
        console.print(f'claude mcp add --transport http krbi {info["endpoint"]} --header "Authorization: Bearer <KRBI_MCP_TOKEN>"')
    if client in ("all", "chatgpt"):
        console.print("\n[bold]ChatGPT[/]")
        console.print(f"Add a custom MCP app using the remote endpoint {info['endpoint']} and the bearer-token authentication method in the supported workspace UI.")


def tunnel_configure(provider: str | None, subdomain: str | None, port: int) -> None:
    manager = TunnelManager()
    if not provider:
        provider = pick("Choose tunnel provider — ↑/↓, Enter", list(PROVIDERS))
    if provider not in PROVIDERS:
        console.print(f"[red]Unknown tunnel provider:[/] {provider}")
        return
    if subdomain is None:
        subdomain = console.input("Subdomain (Enter for automatic): ").strip()
    cfg = manager.configure(provider=provider, subdomain=subdomain, port=port)
    settings = load_settings()
    settings.tunnel_provider = cfg["provider"]
    settings.tunnel_subdomain = cfg["subdomain"]
    settings.tunnel_port = int(cfg["port"])
    save_settings(settings)
    console.print(f"[green]Saved tunnel configuration:[/] {cfg['provider']} · port {cfg['port']} · subdomain {cfg['subdomain'] or 'automatic'}")
    console.print(f"[dim]{PROVIDERS[provider].hint}[/]")


def tunnel_start(provider: str | None, subdomain: str | None, port: int) -> None:
    manager = TunnelManager()
    if provider is None or subdomain is None:
        stored = manager.load()
        provider = provider or stored.get("provider")
        subdomain = subdomain if subdomain is not None else stored.get("subdomain", "")
    if not provider:
        provider = pick("Choose tunnel provider — ↑/↓, Enter", list(PROVIDERS))
    if subdomain is None:
        subdomain = console.input("Subdomain (Enter for automatic): ").strip()
    try:
        url = manager.start(provider=provider, subdomain=subdomain, port=port)
    except Exception as exc:
        console.print(f"[red]Tunnel failed:[/] {exc}")
        return
    settings = load_settings()
    settings.tunnel_provider = provider
    settings.tunnel_subdomain = subdomain
    settings.tunnel_port = port
    settings.tunnel_url = url
    ensure_mcp_token(settings)
    save_settings(settings)
    console.print(f"[bold green]Tunnel online:[/] {url}")
    console.print(f"MCP endpoint: {url.rstrip('/')}/mcp")
    console.print("Run [bold]krbi mcp info[/] to print the bearer token and connection details.")


def tunnel_status() -> None:
    status = TunnelManager().status()
    table = Table(title="KRBI Tunnel")
    table.add_column("Field"); table.add_column("Value")
    for key in ("running", "provider", "subdomain", "port", "url", "platform", "custom_subdomain"):
        table.add_row(key, str(status.get(key, "")))
    table.add_row("hint", str(status.get("hint", "")))
    console.print(table)


def tunnel_stop() -> None:
    manager = TunnelManager()
    manager.stop()
    console.print("Tunnel stopped.")


def install_version_cmd(version: str) -> None:
    try:
        path = install_version(version)
    except (UpdateError, OSError, ValueError) as exc:
        console.print(f"[red]Version install failed:[/] {exc}")
        return
    console.print(f"[green]Installed {version}:[/] {path}")
    console.print(f"Run it with: PYTHONPATH={path / 'src'} python -m krbi_agent.cli --no-update-check tui")


def chat(registry: ProviderRegistry) -> None:
    provider = pick("Choose provider — ↑/↓, Enter", list(registry.names()))
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
        if prompt == "/tunnel":
            tunnel_status(); continue
        if prompt.startswith("/approval "):
            agent.settings.approval_mode = prompt.split(" ", 1)[1].strip(); console.print(f"approval={agent.settings.approval_mode}"); continue
        if not prompt:
            continue
        console.print("[green]krbi[/] › ", end="")

        async def run_once() -> None:
            async for event in agent.run(chat_id, provider, model, prompt, system_prompt=system, goal=goal, api_key=api_key or None):
                if event.type == "delta":
                    console.print(event.delta, end="")
                elif event.type == "error":
                    console.print(f"\n[red]{event.message}[/]", end="")
            console.print()

        asyncio.run(run_once())


def main() -> None:
    parser = argparse.ArgumentParser(prog="krbi", description="KRBI Agent · provider-neutral AI workspace")
    parser.add_argument("--version", action="store_true", help="Show the current KRBI version")
    parser.add_argument("--no-update-check", action="store_true", help="Skip the startup GitHub update check")
    parser.add_argument("--reinstall", action="store_true", help="Refresh the current GitHub checkout")
    parser.add_argument("--banner", metavar="TEXT", help="Custom launch banner")

    subs = parser.add_subparsers(dest="cmd")
    for name in ("providers", "models", "chat", "tui", "run", "config-example", "benchmark", "reset", "doctor"):
        subs.add_parser(name)

    upd = subs.add_parser("update")
    upd.add_argument("--force", action="store_true")
    subs.add_parser("versions")
    old = subs.add_parser("install-version", help="Download a historical commit-based version without replacing the current checkout")
    old.add_argument("version")

    tunnel = subs.add_parser("tunnel", help="Configure and control public tunnels")
    tunnel_sub = tunnel.add_subparsers(dest="tunnel_cmd")
    tstart = tunnel_sub.add_parser("start")
    tstart.add_argument("--provider", choices=sorted(PROVIDERS))
    tstart.add_argument("--subdomain")
    tstart.add_argument("--port", type=int, default=8787)
    tcfg = tunnel_sub.add_parser("configure")
    tcfg.add_argument("--provider", choices=sorted(PROVIDERS))
    tcfg.add_argument("--subdomain")
    tcfg.add_argument("--port", type=int, default=8787)
    tunnel_sub.add_parser("status")
    tunnel_sub.add_parser("stop")

    mcp = subs.add_parser("mcp", help="Inspect or serve KRBI as an MCP server")
    mcp_sub = mcp.add_subparsers(dest="mcp_cmd")
    mcp_sub.add_parser("tools")
    minfo = mcp_sub.add_parser("info")
    minfo.add_argument("--client", choices=("all", "codex", "claude", "chatgpt"), default="all")
    serve = mcp_sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
    serve.add_argument("--tunnel-provider", choices=sorted(PROVIDERS))
    serve.add_argument("--subdomain")
    serve.add_argument("--tunnel-port", type=int)

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
    if args.cmd == "doctor":
        raise SystemExit(doctor())
    if args.cmd == "versions":
        show_versions(); return
    if args.cmd == "install-version":
        install_version_cmd(args.version); return
    if args.cmd == "tunnel":
        if args.tunnel_cmd == "start":
            tunnel_start(args.provider, args.subdomain, args.port)
        elif args.tunnel_cmd == "configure":
            tunnel_configure(args.provider, args.subdomain, args.port)
        elif args.tunnel_cmd == "status":
            tunnel_status()
        elif args.tunnel_cmd == "stop":
            tunnel_stop()
        else:
            tunnel.print_help()
        return
    if args.cmd == "mcp":
        if args.mcp_cmd in (None, "tools"):
            from .mcp import MCPServer
            for tool in MCPServer().tools_list():
                console.print(f"• {tool['function']['name']} — {tool['function']['description']}")
            return
        if args.mcp_cmd == "info":
            mcp_info(args.client); return
        if args.mcp_cmd == "serve":
            settings = load_settings()
            ensure_mcp_token(settings); save_settings(settings)
            if args.tunnel_provider or args.subdomain:
                manager = TunnelManager()
                try:
                    url = manager.start(provider=args.tunnel_provider, subdomain=args.subdomain, port=args.tunnel_port or args.port)
                    settings.tunnel_provider = args.tunnel_provider or settings.tunnel_provider
                    settings.tunnel_subdomain = args.subdomain or settings.tunnel_subdomain
                    settings.tunnel_port = args.tunnel_port or args.port
                    settings.tunnel_url = url
                    save_settings(settings)
                    console.print(f"[bold green]MCP tunnel:[/] {url}/mcp")
                except Exception as exc:
                    console.print(f"[yellow]Tunnel unavailable; serving locally:[/] {exc}")
            from .web import serve
            serve(args.host, args.port)
            return
    if args.cmd == "update":
        console.print("[dim]Checking GitHub for updates…[/]")
        local, remote = check_for_update(force=args.force)
        if remote is None:
            console.print(f"GitHub update check unavailable. Current: v{local.version} · {local.version_type} · code {local.code}")
        elif remote.code <= local.code:
            console.print(f"Already current: v{local.version} · {local.version_type} · code {local.code}")
        else:
            update_and_restart(["run"])
        return

    banner = args.banner.strip() if args.banner else "KRBI // AGENT"
    console.print(f"[bold cyan]{banner}[/] [dim]v{info.version} · {info.version_type} · code {info.code}[/]")
    if not args.no_update_check:
        local, remote = check_for_update()
        if remote and remote.code > local.code:
            console.print(f"[yellow]Update available:[/] v{remote.version} · {remote.version_type} · code {remote.code}. Updating and restarting…")
            update_and_restart([a for a in sys.argv[1:] if a != "--no-update-check"])

    registry = reg()
    if args.cmd == "providers":
        for name in registry.names():
            console.print(f"• {name} [{registry.configs[name].kind}]")
    elif args.cmd == "models":
        asyncio.run(do_models(registry))
    elif args.cmd == "chat":
        chat(registry)
    elif args.cmd in {"tui", "run"}:
        from .textual_app import run; run()
    elif args.cmd == "config-example":
        from .config import save_example; save_example(); console.print("wrote ~/.krbi/config.toml")
    elif args.cmd == "benchmark":
        async def run_bench() -> None:
            from .benchmark import compare
            pairs = [(n, cfg.models[0]) for n, cfg in registry.configs.items() if cfg.models]
            for result in await compare(registry, pairs[:12]):
                console.print(f"{result.provider}/{result.model}: {'OK' if result.ok else 'FAIL'} {result.seconds:.2f}s {result.chars} chars {result.error}")
        asyncio.run(run_bench())
    elif args.cmd == "reset":
        save_settings(Settings())
        console.print(f"Reset KRBI settings at {SETTINGS_PATH}. Saved chats were preserved.")
    elif args.cmd == "web":
        from .web import serve; serve(args.host, args.port)


if __name__ == "__main__":
    main()
