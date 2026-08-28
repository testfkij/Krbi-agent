from __future__ import annotations

import time
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Input, ListView, ListItem, Button, RichLog
from textual.binding import Binding

from .agent import Agent, DEFAULT_SYSTEM
from .commands import COMMANDS, search_commands
from .providers import ProviderRegistry
from .settings import APPROVAL_MODES, Settings, load_settings, save_settings
from .storage import Store
from .tools import default_tools
from .setup_ui import ProviderPicker, ApiKeyPanel, ModelPicker


class KRBIApp(App):
    TITLE = "KRBI Agent"
    SUB_TITLE = "v1.0.0 · A1 · code 23628 · provider-neutral workspace"
    CSS = """
    Screen { layout: vertical; background: $background; }
    #setup { height: auto; min-height: 7; padding: 1 2; border-bottom: solid $panel; }
    #setup2 { height: auto; }
    #setup_row1, #setup_row2 { height: 3; }
    #brand_banner { width: 24; color: $accent; text-style: bold; padding: 1 1; }
    #provider_value { width: 18; color: $text-muted; padding: 1 0; }
    #model_value { width: 30; color: $text-muted; padding: 1 0; }
    #provider_btn { width: 14; }
    #model_btn { width: 12; }
    #connect_btn { width: 12; }
    #status { height: 2; padding: 0 1; color: $text-muted; }
    #conversation { height: 1fr; border: round $panel; margin: 1 2; padding: 1 2; }
    #palette { height: auto; max-height: 12; border: round $accent; background: $panel; margin: 0 2; display: none; }
    #composer_wrap { height: 6; border: round $accent; margin: 0 2 1 2; padding: 0 1; }
    #composer_title { height: 1; text-style: bold; color: $accent; }
    #composer_row { height: 3; }
    #composer { width: 1fr; }
    #load_models { width: 15; }
    #settings_btn { width: 12; }
    #reset_btn { width: 10; }
    #model { width: 42; }
    .local_hint { color: $success; }
    #setup_overlay { layer: overlay; width: 100%; height: 100%; display: none; background: $background 94%; padding: 2 3; }
    #setup_card { width: 1fr; height: 1fr; padding: 2 3; border: round $accent; background: $panel; }
    #api_key_panel, #model_picker { display: none; }
    #settings_view { height: auto; max-height: 18; border: round $accent; margin: 0 2 1 2; padding: 1; display: none; }
    #settings_title { height: 1; text-style: bold; }
    #settings_modes, #settings_tools { height: auto; }
    .settings_btn { margin-right: 1; }
    .selected_mode { background: $accent; color: $text; }
    .tool_status { width: 1fr; }
    Footer { height: 1; }
    """
    BINDINGS = [
        Binding("ctrl+n", "new_chat", "New chat"), Binding("ctrl+k", "focus_commands", "Commands"),
        Binding("ctrl+l", "clear_chat", "Clear"), Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+s", "open_settings", "Settings"), Binding("pageup", "scroll_chat_up", "Scroll up", show=False), Binding("pagedown", "scroll_chat_down", "Scroll down", show=False), Binding("escape", "close_setup", "Close", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.registry = ProviderRegistry()
        self.settings = load_settings()
        self.store = Store()
        self.agent = Agent(self.registry, self.store, settings=self.settings)
        self.provider = self.settings.default_provider if self.settings.default_provider in self.registry.names() else None
        self.model = self.settings.default_model
        self.api_keys: dict[str, str] = {}
        self.chat_id: str | None = None
        self.sending = False
        self.command_mode = False
        self.goal = ""
        self.system = DEFAULT_SYSTEM
        self._buffer = ""

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="setup"):
            with Horizontal(id="setup_row1"):
                yield Static(self.settings.banner_text, id="brand_banner")
                yield Button("Provider", id="provider_btn", variant="primary")
                yield Static("not connected", id="provider_value")
                yield Button("Model", id="model_btn")
                yield Static("no model", id="model_value")
            with Horizontal(id="setup_row2"):
                yield Button("Connect", id="connect_btn")
                yield Button("Settings", id="settings_btn")
                yield Button("Reset", id="reset_btn")
                yield Static("Enter sends · Ctrl+K commands · Ctrl+S settings", id="status")
            yield Static("LOCAL · Ollama · LM Studio · llama.cpp · vLLM", classes="local_hint")
        with Vertical(id="setup_overlay"):
            with Vertical(id="setup_card"):
                yield ProviderPicker(self.registry.names())
                yield ApiKeyPanel()
                yield ModelPicker()
        yield RichLog(highlight=False, markup=True, wrap=True, auto_scroll=True, id="conversation")
        yield ListView(id="palette")
        with Vertical(id="settings_view"):
            yield Static("SETTINGS", id="settings_title")
            yield Static("Approval mode", id="approval_label")
            with Horizontal(id="settings_modes"):
                for mode in APPROVAL_MODES:
                    yield Button(mode, id=f"approval_{mode}", classes="settings_btn")
            yield Static("Dangerous tools — toggle approval", id="tools_label")
            with VerticalScroll(id="settings_tools"):
                for spec in default_tools().list():
                    if spec.dangerous:
                        yield Button(spec.name, id=f"tool_{spec.name}", classes="settings_btn")
            yield Button("Close settings", id="settings_close")
        with Vertical(id="composer_wrap"):
            yield Static("MESSAGE · Enter sends", id="composer_title")
            with Horizontal(id="composer_row"):
                yield Input(placeholder="Type a message…  / for commands", id="composer")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#conversation", RichLog).write("[bold]KRBI Agent ready.[/] Connect a provider to discover live models.")
        self.query_one("#composer", Input).focus()
        if self.provider:
            self._show_provider(self.provider)
        self._refresh_settings()
        self._status()

    def _status(self) -> None:
        self.query_one("#status", Static).update(
            f"[bold]KRBI[/] · {self.provider or 'no provider'} / {self.model or 'no model'} · "
            f"approval={self.settings.approval_mode} · {'working…' if self.sending else 'ready'}"
        )
        self.query_one("#provider_value", Static).update(self.provider or "not connected")
        self.query_one("#model_value", Static).update(self.model or "no model")

    def open_provider_screen(self) -> None:
        overlay = self.query_one("#setup_overlay", Vertical)
        self.query_one("#provider_picker", ProviderPicker).set_items([(name, name) for name in self.registry.names()])
        self.query_one("#provider_picker", ProviderPicker).styles.display = "block"
        self.query_one("#api_key_panel", ApiKeyPanel).styles.display = "none"
        self.query_one("#model_picker", ModelPicker).styles.display = "none"
        overlay.styles.display = "block"
        self.query_one("#provider_picker_search", Input).focus()

    def close_setup_overlay(self) -> None:
        self.query_one("#setup_overlay", Vertical).styles.display = "none"
        self.query_one("#composer", Input).focus()

    def _provider_selected(self, provider: str) -> None:
        self.provider = provider
        self.model = None
        self.api_keys.pop(provider, None)
        self.query_one("#provider_value", Static).update(provider)
        self.query_one("#model_value", Static).update("no model")
        self.query_one("#provider_picker", ProviderPicker).styles.display = "none"
        self.query_one("#api_key_panel", ApiKeyPanel).set_provider(provider)
        self.query_one("#api_key_panel", ApiKeyPanel).styles.display = "block"
        self.query_one("#model_picker", ModelPicker).styles.display = "none"
        self._status()

    async def _api_key_submitted(self, key: str) -> None:
        if not self.provider:
            return
        self.api_keys[self.provider] = key
        self.notify(f"Requesting models from {self.provider}…")
        try:
            models = await self.registry.get(self.provider, api_key=key or None).list_models()
        except Exception as exc:
            self.notify(f"Model discovery failed: {exc}", severity="error", timeout=8)
            return
        if not models:
            self.notify("No models returned by provider", severity="warning")
            return
        self.query_one("#api_key_panel", ApiKeyPanel).styles.display = "none"
        picker = self.query_one("#model_picker", ModelPicker)
        picker.set_models(models)
        picker.styles.display = "block"
        self.query_one("#model_picker_search", Input).focus()

    def _model_selected(self, model: str) -> None:
        if not model or not self.provider:
            return
        self.model = model
        self.settings.default_provider = self.provider
        self.settings.default_model = model
        save_settings(self.settings)
        self._new_chat()
        self._status()
        self.close_setup_overlay()

    def _show_provider(self, provider: str) -> None:
        self._provider_selected(provider)

    async def _discover_models(self) -> None:
        if not self.provider:
            self.open_provider_screen()
            return
        key = self.api_keys.get(self.provider, "")
        try:
            models = await self.registry.get(self.provider, api_key=key or None).list_models()
        except Exception as exc:
            self.notify(f"Model discovery failed: {exc}", severity="error", timeout=8)
            return
        if models:
            picker = self.query_one("#model_picker", ModelPicker)
            picker.set_models(models)
            self.query_one("#setup_overlay", Vertical).styles.display = "block"
            self.query_one("#provider_picker", ProviderPicker).styles.display = "none"
            self.query_one("#api_key_panel", ApiKeyPanel).styles.display = "none"
            picker.styles.display = "block"
            self.query_one("#model_picker_search", Input).focus()
        else:
            self.notify("No models returned by provider", severity="warning")

    def _new_chat(self) -> None:
        if self.provider and self.model:
            self.chat_id = self.store.new_chat("KRBI chat", self.provider, self.model)

    def action_close_setup(self) -> None:
        if self.query_one("#setup_overlay", Vertical).styles.display == "block":
            self.close_setup_overlay()

    def new_chat(self) -> None:
        self._new_chat()
        self._buffer = "[bold]New KRBI chat.[/]\n"
        self.query_one("#conversation", RichLog).clear(); self.query_one("#conversation", RichLog).write(self._buffer)
        self.query_one("#composer", Input).focus()

    def clear_chat(self) -> None:
        self._buffer = ""
        self.query_one("#conversation", RichLog).clear()

    def reset_session(self) -> None:
        self.provider = None
        self.model = None
        self.api_keys.clear()
        self.chat_id = None
        self.goal = ""
        self.system = DEFAULT_SYSTEM
        self.settings = Settings()
        save_settings(self.settings)
        self._buffer = "[bold]Session reset.[/] Saved chats were preserved.\n"
        self.query_one("#conversation", RichLog).clear(); self.query_one("#conversation", RichLog).write(self._buffer)
        self._refresh_settings()
        self._status()
        self.notify("KRBI session reset; saved chats preserved")

    def focus_commands(self) -> None:
        self.command_mode = True
        self._refresh_commands("")
        self.query_one("#palette", ListView).styles.display = "block"
        self.query_one("#composer", Input).focus()

    def open_settings(self) -> None:
        self.query_one("#settings_view", Vertical).styles.display = "block"
        self._refresh_settings()

    def _refresh_settings(self) -> None:
        self.query_one("#approval_label", Static).update(f"Approval mode: [bold]{self.settings.approval_mode}[/]")
        for mode in APPROVAL_MODES:
            btn = self.query_one(f"#approval_{mode}", Button)
            btn.remove_class("selected_mode")
            if mode == self.settings.approval_mode:
                btn.add_class("selected_mode")
        for spec in default_tools().list():
            if not spec.dangerous:
                continue
            btn = self.query_one(f"#tool_{spec.name}", Button)
            if spec.name in self.settings.approved_tools:
                btn.label = f"✓ {spec.name} · approved"
            else:
                btn.label = f"○ {spec.name} · approval required"

    def _refresh_commands(self, query: str) -> None:
        lv = self.query_one("#palette", ListView)
        lv.clear()
        for command in search_commands(query):
            lv.append(ListItem(Static(f"{command.name}  —  {command.description}")))

    def _hide_palette(self) -> None:
        self.command_mode = False
        self.query_one("#palette", ListView).styles.display = "none"

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "composer":
            if event.value.startswith("/"):
                self.command_mode = True
                self._refresh_commands(event.value)
                self.query_one("#palette", ListView).styles.display = "block"
            elif self.command_mode:
                self._hide_palette()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "composer":
            await self._submit()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        ident = event.button.id or ""
        if ident == "provider_btn":
            self.open_provider_screen()
        elif ident == "model_btn":
            await self._discover_models()
        elif ident == "connect_btn":
            self.open_provider_screen()
        elif ident == "settings_btn":
            self.open_settings()
        elif ident == "reset_btn":
            self.reset_session()
        elif ident == "settings_close":
            self.query_one("#settings_view", Vertical).styles.display = "none"
            self.query_one("#composer", Input).focus()
        elif ident.startswith("approval_"):
            mode = ident.removeprefix("approval_")
            self.settings.approval_mode = mode
            save_settings(self.settings)
            self._refresh_settings()
            self._status()
        elif ident.startswith("tool_"):
            name = ident.removeprefix("tool_")
            if name in self.settings.approved_tools:
                self.settings.approved_tools.remove(name)
            else:
                self.settings.approved_tools.add(name)
            save_settings(self.settings)
            self._refresh_settings()

    async def _submit(self) -> None:
        if self.sending:
            return
        box = self.query_one("#composer", Input)
        text = box.value.strip()
        if not text:
            return
        box.value = ""
        if text.startswith("/"):
            self._handle_slash(text)
            return
        await self._send_text(text)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not self.command_mode:
            return
        items = search_commands(self.query_one("#composer", Input).value)
        idx = event.list_view.index
        if idx is None or idx >= len(items):
            return
        command = items[idx]
        self.query_one("#composer", Input).value = command.name + " "
        self._hide_palette()
        self.query_one("#composer", Input).focus()

    def _handle_slash(self, text: str) -> None:
        name, _, arg = text.partition(" ")
        matches = search_commands(name)
        if not matches:
            self.notify(f"Unknown command: {name}", severity="warning")
            return
        action = matches[0].action
        if action == "help":
            self.notify(" ".join(c.name for c in COMMANDS), timeout=8)
        elif action == "providers":
            self.notify("\n".join(self.registry.names()), timeout=8)
        elif action == "models":
            self.run_worker(self._discover_models())
        elif action == "tools":
            self.notify("Tools: " + ", ".join(t.name for t in default_tools().list()), timeout=8)
        elif action == "mcp":
            from .mcp import MCPServer
            self.notify(f"MCP tools: {len(MCPServer().tools_list())}", timeout=5)
        elif action == "goal":
            self.goal = arg.strip()
            self.notify(f"Goal: {self.goal or 'not set'}")
        elif action == "system":
            self.system = arg.strip() or self.system
            self.notify("System prompt updated")
        elif action == "banner":
            if arg.strip():
                self.settings.banner_text = arg.strip()[:120]
                save_settings(self.settings)
                self.query_one("#brand_banner", Static).update(self.settings.banner_text)
                self.notify("Banner updated")
            else:
                self.notify(self.settings.banner_text, timeout=5)
        elif action == "approve" and arg.strip():
            self.settings.approved_tools.add(arg.strip())
            save_settings(self.settings)
            self._refresh_settings()
            self.notify(f"Approved: {arg.strip()}")
        elif action == "revoke" and arg.strip():
            self.settings.approved_tools.discard(arg.strip())
            save_settings(self.settings)
            self._refresh_settings()
            self.notify(f"Revoked: {arg.strip()}")
        elif action == "approval" and arg.strip() in APPROVAL_MODES:
            self.settings.approval_mode = arg.strip()
            save_settings(self.settings)
            self._refresh_settings()
            self._status()
            self.notify(f"Approval mode: {arg.strip()}")
        elif action == "settings":
            self.open_settings()
        elif action == "provider":
            provider = arg.strip()
            if not provider:
                self.open_provider_screen()
            elif provider in self.registry.names():
                self._provider_selected(provider)
            else:
                self.notify("Unknown provider: " + provider, severity="warning")
        elif action == "model":
            if not arg.strip():
                self._discover_models()
            else:
                self.model = arg.strip()
                self._new_chat(); self._status()
                self.notify(f"Model: {self.model}")
        elif action == "new":
            self.new_chat()
        elif action == "clear":
            self.clear_chat()
        elif action == "reset":
            self.reset_session()
        elif action == "local":
            local = [name for name in self.registry.names() if name in {"ollama", "lm-studio", "llama-cpp", "vllm-local"}]
            self.notify("Local providers: " + (", ".join(local) or "none"), timeout=6)
        elif action == "quit":
            self.exit()
        elif action == "tokens":
            self.notify("Token usage is written to the current Markdown session when the provider reports it.", timeout=6)
        elif action == "history":
            self.notify("Sessions: " + ", ".join(c.title for c in self.store.chats()[-8:]), timeout=8)
        elif action == "export":
            if self.chat_id and self.store.chats():
                self.notify(f"Session file: {self.store.chats()[-1].path}", timeout=6)

    async def _send_text(self, text: str) -> None:
        if not self.provider or not self.model:
            self.notify("Choose provider → enter API key → Load models → choose model", severity="warning")
            return
        if not self.chat_id:
            self._new_chat()
        self.sending = True
        self._status()
        self._hide_palette()
        view = self.query_one("#conversation", RichLog)
        view.write(f"\n[bold cyan]you ›[/] {text}")
        view.write("[bold green]krbi ›[/] ", end="")
        pending: list[str] = []
        last_flush = time.monotonic()
        key = self.api_keys.get(self.provider)
        try:
            async for event in self.agent.run(self.chat_id, self.provider, self.model, text, system_prompt=self.system, goal=self.goal, api_key=key):
                if event.type == "delta":
                    pending.append(event.delta)
                    now = time.monotonic()
                    if now - last_flush >= max(self.settings.stream_redraw_ms, 40) / 1000:
                        view.write("".join(pending), end="", scroll_end=True)
                        pending.clear()
                        last_flush = now
                elif event.type == "tool_result":
                    # Tool internals never enter the conversation transcript.
                    self.notify(f"Tool completed: {event.message}", timeout=2)
                elif event.type == "error":
                    view.write(f"[red]\n{event.message}[/]")
            if pending:
                view.write("".join(pending), end="", scroll_end=True)
            view.write("", end="\n", scroll_end=True)
        finally:
            self.sending = False
            self._status()
            self.query_one("#composer", Input).focus()

    def scroll_chat_up(self) -> None:
        self.query_one("#conversation", RichLog).scroll_page_up()

    def scroll_chat_down(self) -> None:
        self.query_one("#conversation", RichLog).scroll_page_down()


def run() -> None:
    KRBIApp().run()
