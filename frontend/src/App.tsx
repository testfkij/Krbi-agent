import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";

type ChatLine = { id: number; role: "user" | "assistant" | "system"; content: string };
type Skill = { name: string; description: string; path: string };
type Role = { id: string; label: string };
const COMMANDS = [
  ["/help", "Show commands"], ["/focus", "Stay on a task until completion"], ["/unfocus", "Release focus mode"],
  ["/role", "Choose specialist role"], ["/skills", "List skill files"], ["/tool-build", "Ask the model to design a custom tool"],
  ["/provider", "Connect an AI provider"], ["/models", "Discover live models"], ["/providers", "List providers"],
  ["/tools", "List available tools"], ["/goal", "Set current goal"], ["/system", "Set system prompt"],
  ["/approval", "Change approval mode"], ["/approve", "Approve a tool"], ["/revoke", "Revoke a tool"],
  ["/settings", "Open settings"], ["/mcp", "Show MCP details"], ["/tunnel", "Show tunnel status"],
  ["/history", "Show saved chats"], ["/export", "Show chat export"], ["/new", "Start a new chat"],
  ["/clear", "Clear visible transcript"], ["/reset", "Reset current session"]
] as const;

async function postForm(path: string, data: Record<string, string>) {
  return fetch(path, { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body: new URLSearchParams(data) });
}

export default function App() {
  const [providers, setProviders] = useState<string[]>([]);
  const [provider, setProvider] = useState("");
  const [connectedProvider, setConnectedProvider] = useState("");
  const [model, setModel] = useState("");
  const [models, setModels] = useState<string[]>([]);
  const [apiKey, setApiKey] = useState("");
  const [showConnect, setShowConnect] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [addingProvider, setAddingProvider] = useState(false);
  const [newProvider, setNewProvider] = useState({ name: "", base_url: "", api_key_env: "", model: "" });
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("Ready");
  const [busy, setBusy] = useState(false);
  const [paletteIndex, setPaletteIndex] = useState(0);
  const [focusTask, setFocusTask] = useState("");
  const [activeRole, setActiveRole] = useState("auto");
  const [roles, setRoles] = useState<Role[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [settingsHtml, setSettingsHtml] = useState("");
  const [toolStatus, setToolStatus] = useState("");
  const transcript = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const activeAssistantId = useRef<number | null>(null);
  const nextId = useRef(0);

  const refreshProviders = useCallback(async () => {
    try {
      const response = await fetch("/providers");
      const names = (await response.text()).split("\n").map((v) => v.trim()).filter(Boolean);
      setProviders(names);
      setProvider((old) => old && names.includes(old) ? old : names.includes("openrouter") ? "openrouter" : names[0] || "");
    } catch {
      setStatus("Backend unavailable · start the KRBI web server first");
    }
  }, []);

  useEffect(() => {
    void refreshProviders();
    void fetch("/roles").then((r) => r.ok ? r.json() : []).then(setRoles).catch(() => setRoles([]));
    void fetch("/skills").then((r) => r.ok ? r.json() : []).then(setSkills).catch(() => setSkills([]));
  }, [refreshProviders]);

  useEffect(() => {
    if (stickToBottom.current && transcript.current) transcript.current.scrollTop = transcript.current.scrollHeight;
  }, [lines]);

  const addLine = (role: ChatLine["role"], content: string) => {
    const id = ++nextId.current;
    setLines((previous) => [...previous, { id, role, content }]);
    return id;
  };
  const appendToLine = (id: number, text: string) => {
    setLines((previous) => previous.map((line) => line.id === id ? { ...line, content: line.content + text } : line));
  };

  async function connect() {
    if (!provider) return;
    setStatus("Discovering live models…");
    try {
      const response = await postForm("/connect", { provider, api_key: apiKey });
      const body = await response.text();
      if (!response.ok) throw new Error(body || "Model discovery failed");
      const list = body.split("\n").map((v) => v.trim()).filter(Boolean);
      list.sort((a, b) => Number(!a.includes(":free")) - Number(!b.includes(":free")));
      setModels(list);
      setModel(list[0] || "");
      setConnectedProvider(provider);
      setStatus(list.length + " model(s) · connected to " + provider);
      setShowConnect(false);
      setApiKey("");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    }
  }

  async function saveProvider(event: FormEvent) {
    event.preventDefault();
    setStatus("Saving provider configuration…");
    try {
      const response = await postForm("/providers/add", newProvider);
      const result = await response.text();
      if (!response.ok) throw new Error(result);
      await refreshProviders();
      setProvider(newProvider.name);
      setAddingProvider(false);
      setShowConnect(true);
      setStatus("Provider added. Connect with an API key if required.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    }
  }

  async function chat(prompt: string) {
    if (!connectedProvider || !model) {
      setShowConnect(true);
      setStatus("Connect a provider and select a model before chatting.");
      return;
    }
    addLine("user", prompt);
    const assistantId = addLine("assistant", "");
    activeAssistantId.current = assistantId;
    setBusy(true);
    setStatus(focusTask ? "Focus task active · working…" : "Working…");
    setToolStatus("");
    try {
      const response = await postForm("/chat/stream", { provider: connectedProvider, model, prompt });
      if (!response.ok || !response.body) throw new Error(await response.text() || "Request failed");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let pending = "";
      let frame = 0;
      const flush = () => {
        if (pending) { appendToLine(assistantId, pending); pending = ""; }
        frame = 0;
      };
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        const rows = buffer.split("\n");
        buffer = rows.pop() || "";
        for (const row of rows) {
          if (!row.startsWith("data: ")) continue;
          const value = row.slice(6);
          if (value.startsWith("Tool running: ") || value.startsWith("Tool completed: ")) setToolStatus(value);
          else if (value.startsWith("[error] ")) pending += "\n" + value;
          else pending += value + "\n";
        }
        if (!frame && pending) frame = requestAnimationFrame(flush);
      }
      if (frame) cancelAnimationFrame(frame);
      flush();
      setStatus("Ready" + (focusTask ? " · focus active" : ""));
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setLines((previous) => previous.map((line) => line.id === assistantId ? { ...line, content: line.content + "\n[Request error] " + message } : line));
      setStatus("Request failed");
    } finally {
      activeAssistantId.current = null;
      setBusy(false);
    }
  }

  async function loadSettings() {
    const response = await fetch("/settings");
    setSettingsHtml(await response.text());
  }

  async function slash(raw: string) {
    const [name, ...rest] = raw.trim().split(" ");
    const arg = rest.join(" ").trim();
    if (name === "/help") { addLine("system", COMMANDS.map(([cmd, description]) => cmd + " — " + description).join("\n")); return; }
    if (name === "/focus") {
      if (!arg) { addLine("system", "Usage: /focus <task to finish>"); return; }
      setFocusTask(arg);
      await postForm("/session", { focus_task: arg });
      addLine("system", "FOCUS ACTIVE\nObjective: " + arg + "\nThe task stays in context until /unfocus.");
      return;
    }
    if (name === "/unfocus") {
      setFocusTask("");
      await postForm("/session", { unfocus: "1" });
      addLine("system", "Focus mode released.");
      return;
    }
    if (name === "/role") {
      const value = arg || "auto";
      if (value !== "auto" && !roles.some((role) => role.id === value)) { addLine("system", "Roles: " + roles.map((role) => role.id).join(", ")); return; }
      setActiveRole(value);
      await postForm("/session", { role: value === "auto" ? "" : value });
      addLine("system", "Assigned specialist: " + value);
      return;
    }
    if (name === "/skills") { addLine("system", skills.map((skill) => skill.name + " · " + skill.path).join("\n") || "No skill files found."); return; }
    if (name === "/tool-build") {
      if (!arg) { addLine("system", "Usage: /tool-build <describe the tool you need>"); return; }
      setBusy(true); setStatus("Model is designing a safe custom tool…");
      try {
        const response = await postForm("/tools/build", { request: arg });
        const result = await response.text();
        if (!response.ok) throw new Error(result);
        addLine("system", "Custom tool saved and registered:\n" + result);
        setToolStatus("Custom tool registered");
      } catch (error) { addLine("system", "Tool build failed: " + (error instanceof Error ? error.message : String(error))); }
      finally { setBusy(false); setStatus("Ready"); }
      return;
    }
    if (name === "/provider" || name === "/models") { setShowConnect(true); return; }
    if (name === "/providers") { addLine("system", "Providers: " + providers.join(", ")); return; }
    if (name === "/tools") { addLine("system", await fetch("/tools").then((response) => response.text())); return; }
    if (name === "/settings") { await loadSettings(); setShowSettings(true); return; }
    if (name === "/goal" || name === "/system") {
      const response = await postForm("/session", name === "/goal" ? { goal: arg } : { system: arg });
      addLine("system", await response.text()); return;
    }
    if (name === "/approval" || name === "/approve" || name === "/revoke") {
      const response = await postForm("/settings", { action: name.slice(1), value: arg });
      addLine("system", await response.text()); return;
    }
    if (name === "/tunnel") { addLine("system", await fetch("/tunnel").then((response) => response.text())); return; }
    if (name === "/mcp") { addLine("system", await fetch("/mcp-info").then((response) => response.text())); return; }
    if (name === "/history") { addLine("system", await fetch("/history").then((response) => response.text())); return; }
    if (name === "/export") { addLine("system", await fetch("/export").then((response) => response.text())); return; }
    if (name === "/clear") { setLines([]); return; }
    if (name === "/new") {
      if (focusTask) { addLine("system", "Focus is active. Complete it or use /unfocus first."); return; }
      await postForm("/session", { new_chat: "1" }); setLines([]); return;
    }
    if (name === "/reset") {
      if (focusTask) { addLine("system", "Focus is active. Use /unfocus before resetting."); return; }
      await postForm("/session", { reset: "1" }); setLines([]); setConnectedProvider(""); setModel(""); setFocusTask(""); return;
    }
    addLine("system", "Unknown command: " + name + " · use /help");
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    const value = input.trim();
    if (!value || busy) return;
    setInput("");
    if (value.startsWith("/")) await slash(value);
    else await chat(value);
  }

  const matches = input.startsWith("/") ? COMMANDS.filter(([command, label]) => (command + " " + label).toLowerCase().includes(input.toLowerCase())) : [];
  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (matches.length) {
      if (event.key === "ArrowDown") { event.preventDefault(); setPaletteIndex((i) => Math.min(i + 1, matches.length - 1)); }
      if (event.key === "ArrowUp") { event.preventDefault(); setPaletteIndex((i) => Math.max(i - 1, 0)); }
      if (event.key === "Tab" || (event.key === "Enter" && !input.includes(" "))) {
        event.preventDefault(); setInput(matches[paletteIndex][0] + " ");
      }
    }
  }

  return <main className="app-shell">
    <header className="topbar">
      <div className="brand-mark">K<span>R</span>BI</div>
      <div className="brand-copy"><strong>KRBI Agent</strong><small>terminal workspace <i className="tiny-dot" /> local-first</small></div>
      <div className="top-meta"><span className="status-led" />{busy ? "WORKING" : "READY"}<span className="version-chip">1.4.0 · A4</span></div>
    </header>
    <section className="workspace-strip">
      <label>PROVIDER<select value={provider} onChange={(event) => setProvider(event.target.value)}>{providers.map((name) => <option key={name}>{name}</option>)}</select></label>
      <label>MODEL<select value={model} onChange={(event) => setModel(event.target.value)}><option value="">Select model</option>{models.map((name) => <option key={name} value={name}>{name}</option>)}</select></label>
      <button className="button button-bright" onClick={() => setShowConnect(true)}>{connectedProvider === provider ? "Connected" : "Connect"}</button>
      <button className="button button-quiet" onClick={() => { void loadSettings(); setShowSettings((value) => !value); }}>Settings</button>
    </section>
    {focusTask && <div className="focus-strip"><span>FOCUS TASK</span><strong>{focusTask}</strong><button className="text-button" onClick={() => void slash("/unfocus")}>Release</button></div>}
    <section className="conversation-frame" ref={transcript} onScroll={(event) => { const el = event.currentTarget; stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 70; }} aria-live="polite">
      {lines.length === 0 && <div className="welcome"><div className="welcome-glyph">›_</div><p className="eyebrow">KRBI // AGENT</p><h1>What are we building?</h1><p className="muted-copy">Ask a question, work on code, inspect a project, or keep an objective active with <code>/focus</code>.</p><div className="suggestions">{["/help", "/skills", "Review this code for issues"].map((value) => <button key={value} className="suggestion" onClick={() => value.startsWith("/") ? void slash(value) : setInput(value)}>{value}<span>↗</span></button>)}</div></div>}
      {lines.map((line) => <article key={line.id} className={"message " + line.role}><div className="message-label">{line.role === "user" ? "YOU" : line.role === "assistant" ? "KRBI" : "SYSTEM"}<span>{line.role === "assistant" ? " · agent" : ""}</span></div><pre>{line.content}{line.role === "assistant" && busy && activeAssistantId.current === line.id ? <i className="stream-caret" /> : null}</pre></article>)}
      {busy && <div className="activity-line"><span className="spinner" />{toolStatus || (focusTask ? "Working on focused objective…" : "Thinking…")}</div>}
    </section>
    {showSettings && <section className="settings-panel">
      <div className="panel-heading"><div><p className="eyebrow">WORKSPACE</p><h2>Settings & integrations</h2></div><button className="icon-button" onClick={() => setShowSettings(false)} aria-label="Close settings">×</button></div>
      <div className="settings-grid">
        <div className="settings-section"><h3>Specialist roles</h3><p>Choose a default role or use task-aware routing.</p><select value={activeRole} onChange={(event) => void slash("/role " + event.target.value)}><option value="auto">Automatic routing</option>{roles.map((role) => <option key={role.id} value={role.id}>{role.label}</option>)}</select></div>
        <div className="settings-section"><h3>Skills library</h3><p>{skills.length} Markdown skills discovered.</p><div className="chips">{skills.slice(0, 10).map((skill) => <span key={skill.name} className="skill-chip">{skill.name}</span>)}</div></div>
        <div className="settings-section"><h3>AI connections</h3><p>Add OpenAI-compatible gateways and local or hosted AI services.</p><button className="button" onClick={() => setAddingProvider((value) => !value)}>Add provider</button>{addingProvider && <form className="provider-form" onSubmit={saveProvider}><input value={newProvider.name} onChange={(e) => setNewProvider({ ...newProvider, name: e.target.value })} placeholder="provider-name" required pattern="[a-zA-Z0-9_-]+" /><input value={newProvider.base_url} onChange={(e) => setNewProvider({ ...newProvider, base_url: e.target.value })} placeholder="https://host.example/v1" type="url" required /><input value={newProvider.api_key_env} onChange={(e) => setNewProvider({ ...newProvider, api_key_env: e.target.value })} placeholder="API_KEY environment variable (optional)" /><input value={newProvider.model} onChange={(e) => setNewProvider({ ...newProvider, model: e.target.value })} placeholder="Optional model ID" /><button className="button button-bright">Save connection</button></form>}</div>
        <div className="settings-section"><h3>Custom tools</h3><p>Ask the active model to generate a small, validated helper.</p><button className="button" onClick={() => { setShowSettings(false); setInput("/tool-build "); }}>Build with AI</button></div>
      </div>
      {settingsHtml && <div className="raw-settings" dangerouslySetInnerHTML={{ __html: settingsHtml }} />}
    </section>}
    <footer className="composer-zone">
      <div className="composer-shell"><span className="prompt-chevron">›</span><form onSubmit={submit} className="composer-form"><input value={input} onChange={(event) => { setInput(event.target.value); setPaletteIndex(0); }} onKeyDown={onKeyDown} placeholder={busy ? "Working… wait for the current task" : "Message KRBI… · / for commands"} aria-label="Message KRBI" /></form><span className="key-hint">ENTER ↵</span></div>
      {matches.length > 0 && <div className="command-palette" role="listbox" aria-label="Slash commands">{matches.slice(0, 7).map(([command, label], index) => <button key={command} role="option" aria-selected={index === paletteIndex} className={index === paletteIndex ? "command-option selected" : "command-option"} onMouseDown={(event) => event.preventDefault()} onClick={() => setInput(command + " ")}><strong>{command}</strong><span>{label}</span><kbd>↵</kbd></button>)}</div>}
      <div className="footer-meta"><span>{status}</span><span>{focusTask ? "FOCUS ACTIVE · /unfocus to release" : "ENTER sends · ↑ ↓ selects commands"}</span></div>
    </footer>
    {showConnect && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowConnect(false); }}><section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="connect-title"><div className="panel-heading"><div><p className="eyebrow">MODEL ROUTER</p><h2 id="connect-title">Connect an AI</h2></div><button className="icon-button" onClick={() => setShowConnect(false)} aria-label="Close">×</button></div><label>Provider<select value={provider} onChange={(event) => setProvider(event.target.value)}>{providers.map((name) => <option key={name}>{name}</option>)}</select></label><label>API key <span className="muted-inline">session only · not saved to disk</span><input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="Optional for local models" autoComplete="off" /></label><label>Model<select value={model} onChange={(event) => setModel(event.target.value)}><option value="">Load models to discover…</option>{models.map((name) => <option key={name} value={name}>{name}</option>)}</select></label><div className="modal-actions"><button className="button" onClick={() => setShowConnect(false)}>Cancel</button><button className="button button-bright" onClick={() => void connect()} disabled={!provider || busy}>Load live models</button></div>{models.length > 0 && <p className="muted-copy">{models.length} model(s) loaded. Choose one to start.</p>}</section></div>}
  </main>;
}
