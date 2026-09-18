# Release KRBI Agent

GitHub main is the release source for KRBI Agent. The current release line is 1.3.2 · A3 · 23633.

Verify:

    PYTHONPATH=src python -m compileall -q src tests
    PYTHONPATH=src python -m pytest -q

The test suite also parses package modules with Python 3.11 grammar to catch syntax accepted by newer Python versions.

Publish:

1. Commit and push source.
2. Record the exact source commit in versions.json.
3. Commit and push the manifest.
4. Verify the CI matrix and Source Release Validation succeed.

KRBI does not require Git tags for historical versions. update.txt identifies the active release, while versions.json maps every release to an immutable Git commit.

Historical installs remain beside the active checkout:

    krbi versions
    krbi install-version <version>

Recovery:

    krbi --reinstall

Creator credit:

Keep the MIT License and NOTICE.md together so the original creator credit remains attached to the project.
