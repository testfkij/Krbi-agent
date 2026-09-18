# KRBI Agent — Release Notes

## 1.3.1 · A3 · 23632

### Release fixes
- Fix the TUI MCP connection-info f-string so the package compiles on Python 3.11+.
- Fix the GitHub source-release workflow so pytest is installed before validation.
- Keep the release manifest commit-based and tagless.
- Retain the 1.3.0 runtime hardening and diagnostics improvements.

## 1.3.0 · A3 · 23631

### Stability
- Add a runtime doctor command for Python, dependency, Git, provider, and tunnel-client checks.
- Improve bounded queue metrics, shutdown behavior, cancellation handling, and worker lifecycle.
- Persist tunnel process IDs so a later CLI invocation can inspect/stop an existing tunnel.
- Clean up failed tunnel launches instead of leaving orphaned processes.

## 1.2.0 · A2 · 23630
Previous release line for queue, MCP HTTP, tunnel adapters, responsive UI, and commit-based version installation.

## 1.0.1 · A1 · 23629
Previous release line.

## 1.0.0 · A1 · 23628
Initial public release line.
