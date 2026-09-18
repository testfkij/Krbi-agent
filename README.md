# KRBI Agent

KRBI Agent is a provider-neutral AI workspace for the terminal, browser, local models, and remote MCP clients.

**Current release:** 1.2.0 · A2 · 23630

## Platforms

The project is designed for Python 3.11+ on Linux and Windows, plus Android/Termux where Python, Rich, Textual, and the required provider tools are available. The CLI uses standard Python path/process APIs, and tunnel process handling adapts to Windows and POSIX systems.

## Start

Run directly from the source checkout:

```bash
cd ~/krbi-agent
PYTHONPATH=src python -m krbi_agent.cli --help
```

Or install the editable package on Linux/Windows:

```bash
python -m pip install -e .
krbi --help
```

Terminal chat:

```bash
krbi chat
```

Full-screen TUI:

```bash
krbi tui
```

Browser/mobile UI:

```bash
krbi web --host 127.0.0.1 --port 8787
```

## Providers and models

KRBI discovers live provider model catalogs instead of depending on a fixed model list. Provider adapters include OpenAI-compatible services, Anthropic, Google Gemini, Azure OpenAI, OpenRouter, Groq, Mistral, DeepSeek, Together, Fireworks, xAI, Cohere, Ollama, LM Studio, llama.cpp, and vLLM.

The TUI and browser model selectors support searching the live catalog. OpenRouter free models are surfaced first when returned by the provider.

## Tools and queue

Agent tool execution is bounded by an async priority queue with configurable worker limits. Read-only tools are available immediately; write/shell tools remain protected by the approval system.

Tool failures are returned to the agent as structured errors so one failed call does not crash the whole run.

## MCP

KRBI exposes MCP over both stdio and authenticated Streamable HTTP at `/mcp`.

Start a local MCP server:

```bash
krbi mcp serve --host 127.0.0.1 --port 8787
```

Print the endpoint and bearer token:

```bash
krbi mcp info
```

The remote HTTP endpoint requires a bearer token, and remote requests cannot override dangerous-tool approval from the server side.

The MCP transport supports the 2026-07-28 protocol plus 2025-11-25 legacy initialization. MCP's current official remote transport is Streamable HTTP; legacy HTTP+SSE is deprecated in the 2026-07-28 specification.

ChatGPT custom MCP apps can use a remote MCP endpoint in supported workspaces. Codex and Claude clients can use Streamable HTTP with the endpoint and Authorization header.

## Tunnel providers

Choose and save a tunnel provider and optional subdomain:

```bash
krbi tunnel configure
krbi tunnel start
krbi tunnel status
krbi tunnel stop
```

Supported adapters are Cloudflare Tunnel, LocalTunnel, ngrok, and Serveo/SSH when their client is installed. Provider credentials remain controlled by the provider's own CLI.

For one-command MCP exposure:

```bash
krbi mcp serve --host 127.0.0.1 --port 8787 --tunnel-provider cloudflared
```

The selected provider, subdomain, port, and last URL are stored under `~/.krbi` for later reuse. The public URL is the MCP base; append `/mcp`.

## Updates and historical versions

KRBI updates the active Git checkout from `origin/main` without using package-registry fallback installers.

```bash
krbi update
```

Historical versions are **commit based**, not Git-tag based. The manifest in `versions.json` maps a version to an immutable Git commit. Install an older copy beside the current checkout:

```bash
krbi versions
krbi install-version 1.0.1
```

The current checkout stays installed and unchanged; historical versions are placed under `~/.krbi/versions/<version>`.

Skip an automatic update check for one launch:

```bash
krbi --no-update-check tui
```

## UI

The browser UI is responsive for desktop, tablet, and narrow mobile widths and honors reduced-motion preferences. The Textual UI uses searchable provider/model panels, keyboard navigation, bounded streaming redraws, and compact tool status notifications.

## Security

API keys entered through the TUI or browser are session-scoped. MCP remote access is bearer-token protected. Dangerous tool permissions are enforced locally by KRBI settings.

## License

KRBI Agent is released under the MIT License with the original creator credit preserved in `NOTICE.md`.
