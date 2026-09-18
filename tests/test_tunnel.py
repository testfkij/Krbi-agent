from krbi_agent.tunnel import TunnelManager, PROVIDERS

def test_tunnel_provider_registry():
    assert {"cloudflared", "localtunnel", "ngrok", "serveo"} <= set(PROVIDERS)
    manager = TunnelManager()
    cfg = manager.configure(provider="cloudflared", subdomain="demo", port=8787)
    assert cfg["provider"] == "cloudflared"
    assert cfg["subdomain"] == "demo"
    assert cfg["port"] == "8787"
