# Release KRBI Agent

GitHub main is the release source for KRBI Agent. The current release line is 1.3.1 · A3 · 23632.

## Verify

    PYTHONPATH=src python -m compileall -q src tests
    PYTHONPATH=src pytest -q tests/test_agent.py tests/test_updater.py tests/test_queue.py tests/test_versions.py tests/test_mcp.py tests/test_mcp_http.py tests/test_tunnel.py tests/test_provider_discovery.py tests/test_settings.py tests/test_tools.py tests/test_web_ui.py tests/test_doctor.py

GitHub CI runs the supported test matrix after every push.

## Publish

KRBI does not require Git tags for historical versions. update.txt defines the active release identity and versions.json maps each release to an immutable Git commit.

For each release:
1. Commit and push source.
2. Record that exact source commit in versions.json.
3. Commit and push the manifest.
4. Verify both GitHub workflows complete successfully.

Historical installs use the recorded commit and remain beside the current checkout.

## Recovery

A local checkout can be refreshed with krbi --reinstall. Historical copies can be installed with krbi install-version <version> without replacing the current checkout.

## Creator credit

Keep the MIT License and NOTICE.md together so the original creator credit remains attached to the project.
