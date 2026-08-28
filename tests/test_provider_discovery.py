from __future__ import annotations
import asyncio, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from krbi_agent.providers import ProviderConfig, ProviderRegistry
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        assert self.headers.get('authorization') == 'Bearer test-key'
        if urlparse(self.path).path == '/models':
            body=b'{"data":[{"id":"live-model-a"},{"id":"live-model-b"}]}'
            self.send_response(200); self.send_header('content-type','application/json'); self.send_header('content-length',str(len(body))); self.end_headers(); self.wfile.write(body)
        else:
            self.send_response(404); self.end_headers()
    def log_message(self,*args): pass
def test_runtime_api_key_and_model_discovery():
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler); threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        p=ProviderConfig('local','openai-compatible',f'http://127.0.0.1:{server.server_address[1]}',models=['fallback'])
        async def run(): return await ProviderRegistry({'local':p}).get('local',api_key='test-key').list_models()
        models=asyncio.run(run()); assert [m.id for m in models] == ['live-model-a','live-model-b']
    finally: server.shutdown(); server.server_close()
