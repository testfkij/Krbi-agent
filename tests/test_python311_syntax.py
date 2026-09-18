from pathlib import Path
import ast


def test_source_parses_with_python_311_grammar():
    root = Path("src/krbi_agent")
    for path in root.glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 11))
