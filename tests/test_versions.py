from pathlib import Path
from krbi_agent.updater import parse_update_text

def test_release_marker_is_1_3_2():
    info = parse_update_text(Path("update.txt").read_text())
    assert info.version == "1.3.2"
    assert info.version_type == "A3"
    assert info.code == 23633

def test_versions_are_commit_based_without_tags():
    data = Path("versions.json").read_text()
    assert '"1.3.1"' in data
    assert '"1.3.0"' in data
    assert '"1.2.0"' in data
    assert '"1.0.1"' in data
