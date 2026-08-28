# Using the KRBI Source Tree

The KRBI repository is a direct source checkout. Run it with `PYTHONPATH=src` from the repository root.

## Validate changes

```bash
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src pytest -q
PYTHONPATH=src python -m krbi_agent.cli --version
```

Keep generated caches out of the repository. Do not add credentials, chat history, temporary update data, or generated release files.

## UI behavior

The chat surface should stay conversation-first. Provider selection, API-key entry, model discovery, Settings, and update progress belong to their own surfaces. Tool internals remain outside the transcript.

## Versioning

The current line is locked at `1.0.0 · A1 · 23628`. Update `update.txt` only when the release identity is intentionally changed.
