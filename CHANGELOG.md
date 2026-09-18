# KRBI Agent — Release Notes

## 1.3.0 · A3 · 23631

### Stability
- Add a runtime doctor command for Python, dependency, Git, provider, and tunnel-client checks.
- Improve bounded queue metrics, shutdown behavior, cancellation handling, and worker lifecycle.
- Persist tunnel process IDs so a later CLI invocation can inspect/stop an existing tunnel.
- Clean up failed tunnel launches instead of leaving orphaned processes.

### CLI
- Add `krbi doctor`.
- Keep tunnel setup, MCP setup, model discovery, and historical-version commands available from the same CLI.
- Improve diagnostics before provider/model work begins.

### MCP and connectivity
- Keep authenticated Streamable HTTP MCP support.
- Keep local dangerous-tool approvals authoritative for remote MCP requests.
- Keep client-specific connection guidance for Codex, Claude Code, and ChatGPT-compatible remote MCP usage.

### Versions
- Release identity is now `1.3.0 · A3 · 23631`.
- Historical versions remain commit based and install beside the active checkout without tags.

## 1.2.0 · A2 · 23630
See previous release notes for queue, MCP HTTP, tunnel adapters, responsive UI, and commit-based version installation.

## 1.0.1 · A1 · 23629
Previous release line.

## 1.0.0 · A1 · 23628
Initial public release line.
