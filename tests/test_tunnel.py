from pathlib import Path
from krbi_agent.tunnel import TunnelManager, PROVIDERS


def test_tunnel_provider_registry(tmp_path):
    assert {"cloudflared", "localtunnel", "ngrok", "serveo"} <= set(PROVIDERS)
    state = tmp_path / "tunnel.toml"
    manager = TunnelManager(state)
    cfg = manager.configure(provider="cloudflared", subdomain="demo", port=9988)
    assert cfg["provider"] == "cloudflared"
    assert cfg["subdomain"] == "demo"
    assert cfg["port"] == "9988"
    loaded = manager.load()
    assert loaded["port"] == "9988"
    assert loaded["pid"] == "0"


def test_tunnel_status_uses_saved_port(tmp_path):
    state = tmp_path / "tunnel.toml"
    manager = TunnelManager(state)
    manager.configure(provider="ngrok", subdomain="demo", port=9911)
    manager.process = None
    assert manager.status()["port"] == 9911
