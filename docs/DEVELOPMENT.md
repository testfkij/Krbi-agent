# Using the KRBI Source Tree

The KRBI repository is a direct source checkout. Run it with `PYTHONPATH=src` from the repository root.

## Validate changes

```bash
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src pytest -q
PYTHONPATH=src python -m krbi_agent.cli --version
```

The CI matrix covers Python 3.11–3.14. The source layout is intentionally dependency-light and works on POSIX systems, including Termux/Android, when Python and the runtime dependencies are installed.

Keep generated caches out of the repository. Do not add credentials, chat history, temporary update data, or generated release files.

## UI behavior

The chat surface should stay conversation-first. Provider selection, API-key entry, model discovery, Settings, and update progress belong to their own surfaces. Tool internals remain outside the transcript.

## Versioning

The current line is `1.0.1 · A1 · 23629`. Update `update.txt` only when the release identity is intentionally changed.
