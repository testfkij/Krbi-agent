# KRBI Agent

KRBI Agent is a provider-neutral AI workspace for the terminal, browser, local models, and remote MCP clients.

Current release: 1.3.2 · A3 · 23633

Highlights:

- Bounded asynchronous tool queue with priority, metrics, graceful shutdown, and cancellation.
- Live model discovery across hosted and local providers.
- Authenticated Streamable HTTP MCP with local dangerous-tool approval.
- Configurable public tunnel adapters and persistent tunnel process state.
- Responsive browser UI and searchable Textual TUI.
- Linux, Windows, and Android/Termux-oriented runtime support.
- Commit-based historical versions that install beside the current release.
- krbi doctor for environment and dependency diagnostics.
- Python 3.11 grammar compatibility validation in tests.

Common commands:

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
    krbi install-version 1.3.1

The active checkout is never replaced by an historical install. Historical source is downloaded from the exact commit recorded in versions.json.

Development:

    python -m compileall -q src tests
    python -m pytest -q

The CI matrix covers Python 3.11–3.14.
