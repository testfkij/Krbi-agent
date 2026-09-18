# Release KRBI Agent

GitHub main is the release source for KRBI Agent. The current release line is 1.3.0 · A3 · 23631.

## Verify the source

    PYTHONPATH=src python -m compileall -q src tests
    PYTHONPATH=src pytest -q tests/test_agent.py tests/test_updater.py tests/test_queue.py tests/test_versions.py tests/test_mcp.py tests/test_mcp_http.py tests/test_tunnel.py tests/test_provider_discovery.py tests/test_settings.py tests/test_tools.py tests/test_web_ui.py tests/test_doctor.py

## Diagnostic check

    PYTHONPATH=src python -m krbi_agent.cli --no-update-check doctor

Tunnel-client warnings are expected when an optional provider CLI is not installed. The doctor command returns success when the core runtime is healthy.

## Publish

KRBI does not require Git tags for historical versions. A release is identified by update.txt, while versions.json maps each released version to an immutable Git commit.

Push main after the source test gate passes:

    git add .
    git commit -m "KRBI Agent 1.3.0"
    git push origin main

Then update versions.json with the final pushed commit for the new release and push that manifest as a second commit. This keeps every historical version mapped to an exact immutable source commit.

## Recovery

A local checkout can be refreshed from GitHub with --reinstall. Historical copies can be installed beside it with krbi install-version <version>.

## Creator credit

Keep the MIT License and NOTICE.md together so the original creator credit remains attached to the project.
