from krbi_agent.doctor import run_checks

def test_doctor_has_core_runtime_checks():
    names = {item.name for item in run_checks()}
    assert {"Python", "httpx", "rich", "textual", "git", "providers"} <= names
