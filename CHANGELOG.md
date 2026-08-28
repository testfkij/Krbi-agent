# KRBI Agent — Release Notes

## 1.0.0 · A1 · 23628

This is the current public release line.

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
- Source-checkout `--reinstall` recovery.
- Restart after an update is applied.

### Release identity

`VERSION=1.0.0`, `VERSION_TYPE=A1`, `CODE=23628`.
