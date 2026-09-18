from pathlib import Path
from krbi_agent.updater import parse_update_text

def test_release_marker_is_1_2_0():
    info = parse_update_text(Path("update.txt").read_text())
    assert info.version == "1.2.0"
    assert info.version_type == "A2"
    assert info.code == 23630

def test_versions_are_commit_based_without_tags():
    data = Path("versions.json").read_text()
    assert '"tagless": true' in data
    assert '"1.0.1"' in data
    assert '"65c0c2fc11b0eb617a047d32ad4202520ec2bc16"' in data
