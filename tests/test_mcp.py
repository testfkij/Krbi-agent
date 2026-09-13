import asyncio
import json

from krbi_agent import __version__
from krbi_agent.mcp import MCPServer


def test_mcp_initialize_uses_package_version():
    async def run():
        response = await MCPServer().handle(
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        )
        assert response["result"]["serverInfo"]["version"] == __version__
        assert response["result"]["capabilities"]["tools"] == {}

    asyncio.run(run())


def test_mcp_tools_list_exposes_workspace_tools():
    async def run():
        response = await MCPServer().handle(
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        )
        names = {item["function"]["name"] for item in response["result"]["tools"]}
        assert {"clock", "system_info", "read_file", "shell"} <= names

    asyncio.run(run())
