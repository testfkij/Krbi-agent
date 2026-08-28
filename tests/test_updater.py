from krbi_agent.updater import UpdateInfo, parse_update_text

def test_update_marker():
    info = parse_update_text("VERSION=1.0.0\nVERSION_TYPE=A1\nCODE=23628\n")
    assert info == UpdateInfo("1.0.0", "A1", 23628)

def test_updater_has_no_package_installer_fallback():
 from pathlib import Path
 text=Path('src/krbi_agent/updater.py').read_text()
 assert 'pip install' not in text
 assert 'def _run_update_pip' not in text


def test_reinstall_requires_github_checkout(monkeypatch):
    import krbi_agent.updater as updater
    monkeypatch.setattr(updater, "_git_root", lambda: None)
    assert updater.reinstall_checkout() is False
