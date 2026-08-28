# Release KRBI Agent

GitHub is the release source for KRBI Agent. The current release line is `1.0.0 · A1 · 23628`.

## Verify the source

```bash
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src pytest -q
PYTHONPATH=src python -m krbi_agent.cli --version
```

## Publish

Commit the source changes and push `main` to GitHub. The release workflow reads the version from `update.txt`, runs the source test gate, creates the version tag when it is missing, and creates the GitHub Release.

```bash
git add .
git commit -m "Release KRBI Agent 1.0.0"
git push origin main --follow-tags
```

## Recovery

A local checkout can be refreshed from GitHub with `--reinstall`. The command is a source checkout recovery action, not a package installation action.

## Creator credit

Keep the MIT License and `NOTICE.md` together so the original creator credit remains attached to the project.
