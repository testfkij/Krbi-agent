from __future__ import annotations

import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from krbi_agent.providers import ProviderConfig, ProviderRegistry


class LocalHandler(BaseHTTPRequestHandler):
    auth_seen = None

    def do_GET(self):
        LocalHandler.auth_seen = self.headers.get("authorization")
        body = b'{"data":[{"id":"local-test-model"}]}'
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


def test_local_openai_compatible_discovery_without_api_key():
    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        config = ProviderConfig("local-test", base_url=f"http://127.0.0.1:{server.server_address[1]}/v1")
        async def run():
            return await ProviderRegistry({"local-test": config}).get("local-test").list_models()
        models = asyncio.run(run())
        assert [model.id for model in models] == ["local-test-model"]
        assert LocalHandler.auth_seen is None
    finally:
        server.shutdown()
        server.server_close()
