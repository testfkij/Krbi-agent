from __future__ import annotations

import asyncio
import html
import secrets
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .agent import Agent, DEFAULT_SYSTEM
from .config import load_configs
from .providers import ProviderRegistry
from .settings import APPROVAL_MODES, Settings, load_settings, save_settings
from .storage import Store
from .tools import default_tools


@dataclass(slots=True)
class WebSession:
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    chat_id: str | None = None
    goal: str = ""
    system: str = DEFAULT_SYSTEM


REGISTRY = ProviderRegistry(load_configs())
SETTINGS = load_settings()
STORE = Store()
AGENT = Agent(REGISTRY, STORE, settings=SETTINGS)
SESSIONS: dict[str, WebSession] = {}
SESSION_LOCK = threading.Lock()

HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KRBI Agent</title>
<style>
:root{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;--bg:#070a0f;--surface:#0d1219;--surface2:#111821;--line:#26313d;--text:#edf2f7;--muted:#8c99a8;--accent:#91a0ff;--good:#79d6a1}
*{box-sizing:border-box}html,body{margin:0;min-height:100%;background:radial-gradient(circle at 50% -10%,#182235 0,#0a0e15 35%,var(--bg) 72%);color:var(--text)}body{min-height:100dvh}
main{width:min(1240px,100%);height:100dvh;margin:auto;display:grid;grid-template-rows:auto auto auto 1fr auto;gap:10px;padding:12px}
header,.panel,.composer{border:1px solid var(--line);background:var(--surface);border-radius:18px;box-shadow:0 12px 40px #0005;backdrop-filter:blur(12px)}
header{padding:14px 16px;display:flex;align-items:center;gap:12px}.brand{font-size:1.06rem;font-weight:850}.sub{margin-top:3px;color:var(--muted);font-size:.78rem}.status{margin-left:auto;color:#aab5c2;font-size:.78rem;text-align:right}.badge{display:inline-flex;align-items:center;font-size:.68rem;padding:4px 7px;border-radius:999px;border:1px solid #394657;vertical-align:middle}.badge.ok{border-color:#327652;color:#9fe2ba;background:#10251b}
.setup{padding:10px;display:grid;grid-template-columns:minmax(150px,.7fr) minmax(210px,1.15fr) auto minmax(190px,1fr) auto;gap:7px}.field,select,button{width:100%;min-height:40px;border:1px solid #303c49;border-radius:11px;background:var(--surface2);color:var(--text);padding:9px 11px;font:inherit}.field::placeholder{color:#687686}.field:focus,select:focus,button:focus{outline:2px solid var(--accent);outline-offset:1px}button{cursor:pointer;font-weight:750;transition:background .12s ease,border-color .12s ease,transform .12s ease}button:hover{background:#18212c;border-color:#526174}button:active{transform:translateY(1px)}button.primary{background:#e9eef7;color:#10141a;border-color:#e9eef7}
.log{min-height:0;overflow:auto;white-space:pre-wrap;border:1px solid var(--line);border-radius:18px;padding:22px clamp(14px,3vw,30px);line-height:1.65;background:linear-gradient(180deg,#0a0f15,#090d13);font-size:.95rem;scroll-behavior:smooth}.log::-webkit-scrollbar{width:8px}.log::-webkit-scrollbar-thumb{background:#26313d;border-radius:20px}.empty{color:#748292;max-width:680px;margin:auto;text-align:center;padding:12vh 10px}
.panel{padding:10px;display:none}.panel h3{margin:0 0 10px}.rows{display:grid;gap:10px}.tool{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:10px 12px;border:1px solid var(--line);border-radius:11px}.muted{color:var(--muted);font-size:.82rem}.tool_status{min-height:20px;padding:0 8px;color:var(--muted);font-size:.78rem}
.composer-wrap{position:relative}.composer{padding:8px;display:flex;gap:7px;align-items:center}.composer input{flex:1;min-width:0;min-height:46px;padding:12px 13px;border-radius:12px;border:1px solid #303c49;background:var(--surface2);color:#fff;font:inherit}.composer button{width:82px}.modal{position:fixed;inset:0;display:none;align-items:center;justify-content:center;padding:18px;background:#02050a99;backdrop-filter:blur(8px);z-index:30}.modal_card{width:min(520px,94vw);padding:18px;border:1px solid #394657;border-radius:18px;background:#0d131b;box-shadow:0 24px 80px #000a}.modal_title{font-weight:850;color:var(--accent);margin-bottom:8px}.modal_card select,.modal_card input{margin-top:8px}.modal_actions{display:flex;gap:8px;margin-top:12px}.modal_actions button{width:1fr}.commands{display:none;position:absolute;left:0;right:0;bottom:62px;border:1px solid #3a4756;border-radius:14px;background:#0f151e;box-shadow:0 18px 45px #0009;max-height:270px;overflow:auto;z-index:10}.cmd{padding:10px 13px;border-bottom:1px solid #202a34}.cmd:last-child{border-bottom:0}.cmd.sel{background:#1a2430}
@media(max-width:900px){main{height:100dvh;padding:8px;gap:8px}.setup{grid-template-columns:1fr 1fr}.setup #connect{grid-column:1/2}.setup #model{grid-column:2/3}.setup #settings{grid-column:1/3}.status{display:none}.log{padding:18px 14px}}
@media(max-width:620px){main{padding:6px;gap:6px}.setup{grid-template-columns:1fr 1fr;padding:7px;border-radius:14px}.setup #provider,.setup #key{grid-column:1/3}.setup #connect,.setup #model{grid-column:auto}.setup #settings{grid-column:1/3}.log{border-radius:14px;padding:15px 12px;font-size:.9rem}.composer{border-radius:14px;padding:6px}.composer input{min-height:44px;font-size:.92rem}.composer button{width:68px}.sub{max-width:72vw;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
@media(max-width:390px){.setup{grid-template-columns:1fr}.setup #provider,.setup #key,.setup #connect,.setup #model,.setup #settings{grid-column:auto}.composer button{width:60px}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
</style></head>
<body><main>
<header><div><div class="brand">KRBI Agent <span class="badge">v1.0.0 · A1 · 23628</span></div><div class="sub">Provider-neutral AI workspace · session-only credentials · local models supported</div></div><div id="status" class="status">Ready</div></header>
<section class="panel" style="display:block"><div class="setup"><select id="provider" aria-label="Provider"></select><button id="connect" class="primary">Connect</button><select id="model" aria-label="Model"><option value="">Choose model</option></select><button id="settings">Settings</button></div></section>
<section id="panel" class="panel"></section>
<section id="connect_modal" class="modal" aria-hidden="true"><div class="modal_card"><div class="modal_title">CONNECT PROVIDER</div><div class="muted" style="margin-bottom:10px">The key stays in this browser session and is used only for provider requests.</div><select id="modal_provider" aria-label="Provider"></select><input id="modal_key" class="field" type="password" autocomplete="off" placeholder="API key"><div class="modal_actions"><button id="modal_cancel">Cancel</button><button id="modal_submit" class="primary">Load live models</button></div></div></section>
<section class="panel" style="display:block;padding:10px 14px"><span class="badge ok">LOCAL</span> Ollama · LM Studio · llama.cpp · vLLM <span class="muted">— no API key required when the local server allows it</span></section>
<section id="log" class="log"><div class="empty">Choose a provider, connect, select a model, then press Enter to send.</div></section><div id="tool_status" class="tool_status" aria-live="polite"></div>
<div class="composer-wrap"><div id="commands" class="commands"></div><div class="composer"><input id="q" autocomplete="off" placeholder="MESSAGE — Enter sends · / for commands"></div></div>
</main>
<script>
const $=id=>document.getElementById(id),p=$('provider'),connect=$('connect'),m=$('model'),log=$('log'),q=$('q'),cmds=$('commands'),panel=$('panel'),status=$('status'),toolStatus=$('tool_status'),modal=$('connect_modal'),modalProvider=$('modal_provider'),modalKey=$('modal_key'),modalSubmit=$('modal_submit'),modalCancel=$('modal_cancel');
let providers=[],selected=0,active='';
const commands=['/help','/goal','/system','/provider','/model','/local','/providers','/models','/tools','/approve','/revoke','/approval','/settings','/mcp','/new','/clear','/reset','/history','/tokens','/export'];
const descriptions={help:'show commands',local:'show local model providers',goal:'set agent goal',system:'set system prompt',provider:'choose provider',model:'choose model',providers:'list providers',models:'reload live models',tools:'show available tools',approve:'approve a dangerous tool',revoke:'revoke a tool approval',approval:'set approval mode',settings:'open settings',mcp:'inspect MCP tools',new:'start a new chat',clear:'clear transcript',history:'show recent sessions',tokens:'explain usage',export:'show session file'};
async function init(){let r=await fetch('/providers');providers=(await r.text()).split('\n').filter(Boolean);let opts=providers.map(x=>new Option(x,x));p.replaceChildren(...opts);modalProvider.replaceChildren(...providers.map(x=>new Option(x,x)));if(providers.includes('openrouter'))p.value='openrouter';else if(providers[0])p.value=providers[0];modalProvider.value=p.value;status.textContent='Connect → live models → choose model → Enter sends';}
function append(x){log.querySelector('.empty')?.remove();log.textContent+=x;log.scrollTop=log.scrollHeight}
function showCommands(){let v=q.value.toLowerCase();let a=commands.filter(x=>x.includes(v));cmds.innerHTML=a.map((x,i)=>`<div class="cmd ${i===selected?'sel':''}"><b>${x}</b> <span class="muted">— ${descriptions[x.slice(1)]||''}</span></div>`).join('');cmds.style.display=a.length?'block':'none'}
async function discover(){let key=modalKey.value;status.textContent='Requesting live available models…';connect.disabled=true;modalSubmit.disabled=true;try{let r=await fetch('/connect',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:new URLSearchParams({provider:modalProvider.value,api_key:key})});let text=await r.text();if(!r.ok){append('\n[error] '+text);status.textContent='Model discovery failed';return}let models=text.split('\n').filter(Boolean);models.sort((a,b)=>Number(!a.includes(':free'))-Number(!b.includes(':free')));m.replaceChildren(...models.map(x=>new Option(x+(x.includes(':free')?' · FREE':''),x)));if(models[0])m.value=models[0];active=modalProvider.value;p.value=active;status.textContent=(models.filter(x=>x.includes(':free')).length||models.length)+' models loaded · '+active;modal.style.display='none';modal.setAttribute('aria-hidden','true');modalKey.value='';}finally{connect.disabled=false;modalSubmit.disabled=false}}
async function chat(v){if(!active||!m.value){status.textContent='Load models before chatting';return}append('\n\nYOU › '+v+'\nKRBI › ');q.value='';status.textContent='Working…';let r=await fetch('/chat/stream',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:new URLSearchParams({provider:active,model:m.value,prompt:v})});if(!r.ok){append('\n[HTTP '+r.status+'] '+await r.text());status.textContent='Error';return}let reader=r.body.getReader(),dec=new TextDecoder(),buf='';while(true){let z=await reader.read();if(z.done)break;buf+=dec.decode(z.value,{stream:true});let ls=buf.split('\n');buf=ls.pop();for(let line of ls)if(line.startsWith('data: ')){if(line.startsWith('data: Tool completed: '))toolStatus.textContent=line.slice(6);else append(line.slice(6));}}status.textContent='Ready'}
function submit(){let v=q.value.trim();if(!v)return;if(v.startsWith('/'))handleSlash(v);else chat(v)}
function handleSlash(v){let [name,...rest]=v.split(' '),arg=rest.join(' ');if(name==='/help'){append('\nCommands: '+commands.join(' '));return}if(name==='/providers'){append('\nProviders: '+providers.join(', '));return}if(name==='/models'){openConnect();return}if(name==='/tools'){fetch('/tools').then(r=>r.text()).then(x=>append('\n'+x));return}if(name==='/local'){append('\nLocal providers: '+providers.filter(x=>['ollama','lm-studio','llama-cpp','vllm-local'].includes(x)).join(', '));return}if(name==='/settings'){openSettings();return}if(['/approve','/revoke','/approval'].includes(name)){applySettings(name,arg);return}if(name==='/goal'){fetch('/session',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:new URLSearchParams({goal:arg})});append('\nGoal updated.');return}if(name==='/system'){fetch('/session',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:new URLSearchParams({system:arg})});append('\nSystem prompt updated.');return}if(name==='/new'||name==='/clear'){log.textContent='';return}if(name==='/reset'){fetch('/session',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:new URLSearchParams({reset:'1'})}).then(()=>{log.textContent='';append('\nSession reset; saved chats preserved.');});return}if(name==='/history'){fetch('/history').then(r=>r.text()).then(x=>append('\n'+x));return}if(name==='/tokens'){append('\nToken usage is recorded when the provider reports usage.');return}if(name==='/export'){fetch('/export').then(r=>r.text()).then(x=>append('\n'+x));return}if(name==='/provider'){let hit=providers.find(x=>x===arg);if(hit){p.value=hit;active='';m.replaceChildren(new Option('Choose model',''));}return}if(name==='/model'){m.value=arg;active=p.value;return}append('\nUnknown command: '+name)}
async function setSetting(action,value){let r=await fetch('/settings',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:new URLSearchParams({action,value})});panel.innerHTML=await r.text()+'<div style=\"margin-top:10px\"><button onclick=\"panel.style.display=\\\'none\\\'\">Close</button></div>';panel.style.display='block'}
async function openSettings(){let x=await fetch('/settings').then(r=>r.text());panel.innerHTML=x+'<div style=\"margin-top:10px\"><button onclick=\"panel.style.display=\\\'none\\\'\">Close</button></div>';panel.style.display='block'}
async function applySettings(name,arg){let r=await fetch('/settings',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:new URLSearchParams({action:name.slice(1),value:arg})});append('\n'+await r.text());}
q.addEventListener('input',()=>{selected=0;if(q.value.startsWith('/'))showCommands();else cmds.style.display='none'});
q.addEventListener('keydown',e=>{if(cmds.style.display==='block'){let els=[...cmds.children];if(e.key==='ArrowDown'){e.preventDefault();selected=Math.min(selected+1,els.length-1);showCommands();return}if(e.key==='ArrowUp'){e.preventDefault();selected=Math.max(selected-1,0);showCommands();return}if(e.key==='Enter'&&els[selected]){e.preventDefault();q.value=els[selected].textContent.trim().split(' ')[0]+' ';cmds.style.display='none';return}}if(e.key==='Enter'){e.preventDefault();submit()}});
p.onchange=()=>{active='';m.replaceChildren(new Option('Choose model',''));modalProvider.value=p.value;};function openConnect(){modalProvider.value=p.value||'openrouter';modal.style.display='flex';modal.setAttribute('aria-hidden','false');modalKey.focus()}
function closeConnect(){modal.style.display='none';modal.setAttribute('aria-hidden','true');q.focus()}
p.onchange=()=>{active='';m.replaceChildren(new Option('Choose model',''));modalProvider.value=p.value;};connect.onclick=openConnect;modalProvider.onchange=()=>p.value=modalProvider.value;modalSubmit.onclick=discover;modalCancel.onclick=closeConnect; $('settings').onclick=openSettings;log.tabIndex=0;log.addEventListener('keydown',e=>{if(e.key==='ArrowUp'){log.scrollTop-=120;e.preventDefault()}else if(e.key==='ArrowDown'){log.scrollTop+=120;e.preventDefault()}else if(e.key==='PageUp'){log.scrollTop-=log.clientHeight*.9;e.preventDefault()}else if(e.key==='PageDown'){log.scrollTop+=log.clientHeight*.9;e.preventDefault()}else if(e.key==='Home'){log.scrollTop=0;e.preventDefault()}else if(e.key==='End'){log.scrollTop=log.scrollHeight;e.preventDefault()}});window.addEventListener('keydown',e=>{if(e.key==='Escape'&&modal.style.display==='flex')closeConnect()});init();
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def _session(self) -> tuple[str, WebSession]:
        cookie = self.headers.get("Cookie", "")
        sid = next((part.strip().split("=", 1)[1] for part in cookie.split(";") if part.strip().startswith("krbi_sid=")), None)
        with SESSION_LOCK:
            if not sid or sid not in SESSIONS:
                sid = secrets.token_urlsafe(18)
                SESSIONS[sid] = WebSession()
            return sid, SESSIONS[sid]

    def _send(self, body: str, status: int = 200, ctype: str = "text/plain; charset=utf-8", sid: str | None = None) -> None:
        data = body.encode()
        self.send_response(status)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(data)))
        self.send_header("cache-control", "no-store")
        if sid:
            self.send_header("set-cookie", f"krbi_sid={sid}; Path=/; HttpOnly; SameSite=Strict")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        sid, session = self._session()
        if path == "/":
            return self._send(HTML, ctype="text/html; charset=utf-8", sid=sid)
        if path == "/health":
            return self._send("ok", sid=sid)
        if path == "/providers":
            return self._send("\n".join(REGISTRY.names()), sid=sid)
        if path == "/tools":
            lines = []
            for tool in default_tools().list():
                state = "APPROVED" if SETTINGS.tool_allowed(tool.name, tool.dangerous) else "approval required"
                lines.append(f"{tool.name} — {state} — {tool.description}")
            return self._send("\n".join(lines), sid=sid)
        if path == "/settings":
            return self._send(self.settings_html(), sid=sid)
        if path == "/history":
            return self._send("\n".join(f"{chat.title} · {chat.provider}/{chat.model}" for chat in STORE.chats()[-10:]) or "No saved sessions.", sid=sid)
        if path == "/export":
            chat = STORE.chats()[-1] if STORE.chats() else None
            return self._send(str(chat.path) if chat else "No session to export.", sid=sid)
        return self._send("not found", 404, sid=sid)

    @staticmethod
    def settings_html() -> str:
        mode_buttons = []
        for mode in APPROVAL_MODES:
            cls = "primary" if mode == SETTINGS.approval_mode else ""
            mode_buttons.append(
                f'<button class="{cls}" onclick="setSetting(\'approval\',\'{html.escape(mode)}\')">{html.escape(mode)}</button>'
            )
        tool_rows = []
        for tool in default_tools().list():
            if not tool.dangerous:
                continue
            approved = tool.name in SETTINGS.approved_tools
            action = "revoke" if approved else "approve"
            label = "Revoke" if approved else "Approve"
            state = "approved" if approved else "approval required"
            badge_class = "badge ok" if approved else "badge"
            tool_rows.append(
                f'<div class="tool"><span><b>{html.escape(tool.name)}</b><br>'
                f'<span class="muted">{html.escape(tool.description)}</span></span>'
                f'<span><span class="{badge_class}">{state}</span> '
                f'<button onclick="setSetting(\'{action}\',\'{html.escape(tool.name)}\')">{label}</button></span></div>'
            )
        tools = "".join(tool_rows) or '<div class="muted">No dangerous tools configured.</div>'
        return (
            '<h3>KRBI Settings</h3><div class="rows">'
            '<div><b>Approval mode</b><div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">'
            + "".join(mode_buttons) + '</div></div>'
            f'<div><b>Workspace:</b> {html.escape(SETTINGS.workspace)}</div>'
            f'<div><b>Dangerous tools</b></div>{tools}</div>'
        )

    def _form(self) -> dict[str, str]:
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length).decode("utf-8", "replace")
        return {key: value[0] for key, value in parse_qs(raw, keep_blank_values=True).items()}

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        sid, session = self._session()
        data = self._form()
        if path == "/connect":
            provider = data.get("provider", "")
            if provider not in REGISTRY.names():
                return self._send("unknown provider", 400, sid=sid)
            try:
                models = asyncio.run(REGISTRY.get(provider, api_key=data.get("api_key") or None).list_models())
            except Exception as exc:
                return self._send(str(exc), 502, sid=sid)
            session.provider = provider
            session.api_key = data.get("api_key") or None
            session.model = models[0].id if models else None
            session.chat_id = None
            return self._send("\n".join(m.id for m in models), sid=sid)
        if path == "/session":
            if data.get("reset") == "1":
                session.provider = None; session.model = None; session.api_key = None; session.chat_id = None; session.goal = ""; session.system = DEFAULT_SYSTEM
                return self._send("session reset", sid=sid)
            if "goal" in data:
                session.goal = data["goal"].strip()
            if "system" in data and data["system"].strip():
                session.system = data["system"].strip()
            return self._send("session updated", sid=sid)
        if path == "/settings":
            action, value = data.get("action"), data.get("value", "").strip()
            if action == "approve" and value:
                SETTINGS.approved_tools.add(value)
            elif action == "revoke" and value:
                SETTINGS.approved_tools.discard(value)
            elif action == "approval" and value in APPROVAL_MODES:
                SETTINGS.approval_mode = value
            else:
                return self._send("invalid settings action", 400, sid=sid)
            save_settings(SETTINGS)
            return self._send(self.settings_html(), sid=sid)
        if path != "/chat/stream":
            return self._send("not found", 404, sid=sid)
        provider = data.get("provider") or session.provider
        model = data.get("model") or session.model
        prompt = data.get("prompt", "").strip()
        if not provider or not model or not prompt:
            return self._send("provider, model and prompt are required", 400, sid=sid)
        if provider not in REGISTRY.names():
            return self._send("unknown provider", 400, sid=sid)
        session.provider, session.model = provider, model
        if not session.chat_id:
            session.chat_id = STORE.new_chat("Web chat", provider, model)
        self.send_response(200)
        self.send_header("content-type", "text/event-stream; charset=utf-8")
        self.send_header("cache-control", "no-cache, no-store")
        self.send_header("connection", "close")
        self.send_header("x-content-type-options", "nosniff")
        self.end_headers()

        async def run() -> None:
            async for event in AGENT.run(session.chat_id, provider, model, prompt, system_prompt=session.system, goal=session.goal, api_key=session.api_key):
                if event.type == "delta":
                    for part in event.delta.splitlines() or [""]:
                        self.wfile.write(("data: " + part + "\n").encode())
                    self.wfile.write(b"\n"); self.wfile.flush()
                elif event.type == "tool_result" and SETTINGS.show_tool_events:
                    self.wfile.write(("data: [tool] " + event.message + "\n\n").encode()); self.wfile.flush()
                elif event.type == "error":
                    self.wfile.write(("data: [error] " + event.message + "\n\n").encode()); self.wfile.flush()

        try:
            asyncio.run(run())
        except (BrokenPipeError, ConnectionResetError):
            return

    def log_message(self, _format: str, *_args) -> None:
        return


def serve(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"KRBI Agent web UI: http://127.0.0.1:{port} (listening on {host})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
