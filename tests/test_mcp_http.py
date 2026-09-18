import asyncio
from krbi_agent.mcp_http import handle_mcp_request, ensure_mcp_token
from krbi_agent.settings import Settings
from krbi_agent.tools import ToolExecutor

def test_mcp_initialize_and_tools_list():
    settings = Settings(mcp_token="test-token")
    tools = ToolExecutor()
    status, headers, body = handle_mcp_request({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2026-07-28"}}, settings, tools)
    assert status == 200
    assert body["result"]["protocolVersion"] == "2026-07-28"
    status, _, body = handle_mcp_request({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}, settings, tools)
    assert status == 200
    assert body["result"]["tools"]

def test_mcp_does_not_allow_remote_dangerous_override():
    settings = Settings(mcp_token="test-token", approval_mode="default")
    tools = ToolExecutor()
    status, _, body = handle_mcp_request({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"shell","arguments":{"command":"echo nope"},"allow_dangerous":True}}, settings, tools)
    assert status == 200
    assert body["error"]["code"] == -32001

def test_mcp_token_generated():
    settings = Settings()
    token = ensure_mcp_token(settings)
    assert len(token) >= 32
