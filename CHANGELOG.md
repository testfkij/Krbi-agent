# KRBI Agent — Release Notes

## 1.2.0 · A2 · 23630

### Agent and queue
- Add a bounded asynchronous priority queue for concurrent tool execution.
- Keep tool failures isolated as structured errors so one call does not crash the agent run.

### MCP
- Add authenticated Streamable HTTP at /mcp.
- Support 2026-07-28 MCP plus 2025-11-25 initialization compatibility.
- Prevent remote callers from overriding KRBI's dangerous-tool approval policy.
- Add CLI connection information for Codex, Claude Code, and ChatGPT custom MCP setup.

### Tunnels
- Add Cloudflare Tunnel, LocalTunnel, ngrok, and Serveo/SSH adapters.
- Save provider, subdomain, port, last URL, and tunnel process state under ~/.krbi.
- Add tunnel configure/start/status/stop and one-command MCP tunnel serving.

### CLI and versions
- Add commit-based, tagless historical version installs.
- Keep older source copies beside the current checkout.
- Add standard pyproject.toml packaging metadata for Linux/Windows installs.

### UI and portability
- Refresh CLI/TUI version markers and MCP visibility.
- Keep browser UI responsive across desktop, tablet, and narrow mobile widths.
- Improve Linux/POSIX and Windows process handling for tunnels.

## 1.0.1 · A1 · 23629

### Reliability and portability
- Keep the MCP server version synchronized with the package release version.
- Validate the source tree on Python 3.14 in CI in addition to the supported 3.11–3.13 matrix.
- Keep the source-checkout workflow compatible with Termux/Android and other POSIX environments.
- Add release smoke coverage for version reporting and MCP initialization.

## 1.0.0 · A1 · 23628

This was the previous public release line.

### Experience
- Clean terminal, TUI, and browser chat surfaces.
- Dedicated provider, API-key, and model selection screens.
- Arrow-key navigation, search, Enter-to-select, and responsive layouts.
- No Send button in the normal chat composer.
- Automatic chat scrolling with manual navigation controls.
- Customizable KRBI banner.

### Providers
- Hosted provider discovery through live model requests.
- OpenRouter free models surfaced first when reported by the provider.
- Local model support for Ollama, LM Studio, llama.cpp, and vLLM.

### Tools
- Tool execution stays inside the agent loop.
- Raw tool traces stay out of the transcript.
- Read-only workspace inspection tools.
- Approval-gated write and shell operations.

### Recovery and updates
- GitHub-backed update checks.
- Source-checkout --reinstall recovery.
- Restart after an update is applied.

### Release identity
VERSION=1.0.0, VERSION_TYPE=A1, CODE=23628.
