# Release KRBI Agent

GitHub main is the release source for KRBI Agent. The current release line is 1.2.0 · A2 · 23630.

## Verify the source

    PYTHONPATH=src python -m compileall -q src tests
    PYTHONPATH=src pytest -q tests/test_agent.py tests/test_updater.py tests/test_queue.py tests/test_versions.py tests/test_mcp.py tests/test_mcp_http.py tests/test_tunnel.py tests/test_provider_discovery.py tests/test_settings.py tests/test_tools.py tests/test_web_ui.py

## Publish

KRBI does not require Git tags for historical versions. A release is identified by update.txt, while versions.json maps each released version to an immutable Git commit.

Push main after the source test gate passes:

    git add .
    git commit -m "KRBI Agent <version>"
    git push origin main

The CI workflow validates the source and produces a commit-based archive artifact. Older versions remain installable beside the current checkout with krbi versions and krbi install-version <version>.

## Recovery

A local checkout can be refreshed from GitHub with --reinstall. The command is a source checkout recovery action, not a package-registry installer.

## Creator credit

Keep the MIT License and NOTICE.md together so the original creator credit remains attached to the project.
