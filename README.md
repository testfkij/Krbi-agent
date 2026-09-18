# KRBI Agent

KRBI Agent is a provider-neutral AI workspace for the terminal, browser, local models, and remote MCP clients.

**Current release:** 1.3.0 · A3 · 23631

## Highlights

- Bounded asynchronous tool queue with priority, metrics, graceful shutdown, and cancellation.
- Live model discovery across hosted and local providers.
- Authenticated Streamable HTTP MCP with local dangerous-tool approval.
- Configurable public tunnel adapters and persistent tunnel state.
- Responsive browser UI and searchable Textual TUI.
- Linux, Windows, and Android/Termux-oriented runtime support.
- Commit-based historical versions that install beside the current release.
- `krbi doctor` for environment and dependency diagnostics.

## Common commands

    krbi doctor
    krbi providers
    krbi models
    krbi tui
    krbi web --host 127.0.0.1 --port 8787

MCP:

    krbi mcp serve --host 127.0.0.1 --port 8787
    krbi mcp info --client codex
    krbi mcp info --client claude

Tunnels:

    krbi tunnel configure
    krbi tunnel start
    krbi tunnel status
    krbi tunnel stop

Historical versions:

    krbi versions
    krbi install-version 1.2.0

The active checkout is never replaced by an historical install. Each historical copy is downloaded from its recorded Git commit.

## Provider/model handling

KRBI asks supported providers for their current model catalog rather than relying only on a fixed list. Local adapters include Ollama, LM Studio, llama.cpp, and vLLM. Hosted adapters include OpenAI-compatible services, Anthropic, Google Gemini, Azure OpenAI, OpenRouter, Groq, Mistral, DeepSeek, Together, Fireworks, xAI, and Cohere.

## MCP security

Remote MCP requests use a bearer token. Dangerous tool permissions are evaluated by local KRBI settings; a remote caller cannot turn on shell/write access by passing a remote override flag.

## Tunnel behavior

Supported tunnel adapters are Cloudflare Tunnel, LocalTunnel, ngrok, and Serveo/SSH when the relevant client is installed. The selected provider, optional subdomain, port, last URL, and process PID are stored under `~/.krbi`.

Cloudflare quick tunnels generate a provider URL automatically; a custom domain requires a configured managed tunnel. Other providers only honor custom subdomains/domains when the provider account and client support them.

## Development

Run:

    python -m compileall -q src tests
    python -m pytest -q

The CI matrix covers Python 3.11–3.14.
