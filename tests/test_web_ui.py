from krbi_agent.web import Handler


def test_web_settings_surface_has_controls():
    body = Handler.settings_html()
    assert "Approval mode" in body
    assert "setSetting('approval'" in body
    assert "write_file" in body
    assert "shell" in body


def test_web_ui_has_local_models_and_reset():
    assert "LOCAL" in __import__("krbi_agent.web", fromlist=["HTML"]).HTML
    assert "/local" in __import__("krbi_agent.web", fromlist=["HTML"]).HTML
    assert "reset" in __import__("krbi_agent.web", fromlist=["HTML"]).HTML

def test_web_chat_has_no_send_button_and_tool_status_is_separate():
 from krbi_agent.web import HTML
 assert '<button id="send"' not in HTML
 assert 'id="tool_status"' in HTML
 assert '[tool]' not in HTML
