# KRBI Agent

KRBI Agent is a provider-neutral AI workspace for the terminal and browser. It connects to hosted APIs or local models, keeps the normal chat view clean, and gives tool use a controlled, visible workflow.

**Current release:** 1.0.0 · A1 · 23628

## Start

Use the source checkout directly. For an existing checkout such as `~/krbi-agent`, there is nothing to reinstall from a package registry.

```bash
cd ~/krbi-agent
PYTHONPATH=src python -m krbi_agent.cli --help
```

Start terminal chat:

```bash
PYTHONPATH=src python -m krbi_agent.cli chat
```

Start the full-screen TUI:

```bash
PYTHONPATH=src python -m krbi_agent.cli tui
```

Start the browser/mobile UI:

```bash
PYTHONPATH=src python -m krbi_agent.cli web --host 127.0.0.1 --port 8787
```

## Provider setup

Open **Provider** or type `/provider`. Search with the keyboard, move with the arrow keys, and press Enter.

After choosing a provider, KRBI opens a dedicated connection screen. The API key does not live in the chat composer. Press Enter after entering the key to request the provider's live model catalog.

Choose a model from the live results and return to chat. OpenRouter free models are shown first when the provider reports them.

Local model providers such as Ollama, LM Studio, llama.cpp, and vLLM can be used without a remote API key when their local server is available.

## Chat controls

The chat composer is intentionally simple: **Enter sends**. There is no Send button in the normal chat view.

The transcript scrolls automatically while a response is arriving. You can still move through it with the mouse, touch scrolling, arrow keys, Page Up/Page Down, Home, and End.

Type `/` to search commands. Useful commands include `/provider`, `/model`, `/models`, `/tools`, `/settings`, `/reset`, `/new`, `/history`, `/local`, `/banner`, and `/quit`.

## Tools

KRBI can call tools during an agent run. Tool arguments and results stay inside the agent loop so the model can continue its work. Raw tool output is not dumped into the chat transcript. The interface only shows a compact completion status.

Read-only tools include time, system information, file inspection, directory listing, file search, and path existence checks. File writes and shell execution require approval unless the selected approval mode explicitly allows them. Workspace paths are sandboxed.

## Settings and banner

The Settings screen controls approval behavior and dangerous-tool approvals. The banner can be customized for the current interface.

CLI example:

```bash
PYTHONPATH=src python -m krbi_agent.cli --banner "MY KRBI WORKSPACE" tui
```

Inside the TUI, use `/banner MY KRBI WORKSPACE` or save the banner from Settings.

## Updates

KRBI uses GitHub as its source and update channel. The local `update.txt` marker is the release authority. A normal launch checks GitHub for a newer code value, fast-forwards the source checkout when one exists, and restarts KRBI.

To skip the network check for one launch:

```bash
PYTHONPATH=src python -m krbi_agent.cli --no-update-check tui
```

To force a clean source refresh from GitHub and restart:

```bash
PYTHONPATH=src python -m krbi_agent.cli --reinstall
```

`--reinstall` refreshes the checkout from `origin/main` and removes untracked project files. User data under `~/.krbi` is kept.

## Version marker

`update.txt` contains:

```text
VERSION=1.0.0
VERSION_TYPE=A1
CODE=23628
```

The 1.0.0 line stays locked until an explicit version change.

## Privacy

API keys entered through the TUI or browser are session-scoped. Chat history is stored as Markdown under `~/.krbi/chats/`. The browser session keeps its active provider credential in memory.

## License

KRBI Agent is released under the MIT License with the original creator credit preserved in `NOTICE.md`.
