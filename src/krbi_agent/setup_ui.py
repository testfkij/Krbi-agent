from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Input, ListItem, ListView, Static

from .core import ModelInfo


class SearchInput(Input):
    def __init__(self, *args, target_id: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_id = target_id

    def on_key(self, event) -> None:
        if event.key == "down":
            self.screen.query_one(f"#{self.target_id}", ListView).focus()
            event.stop()


class SelectList(ListView):
    BINDINGS = [Binding("enter", "select_current", "Select", show=False)]

    def __init__(self, *children, callback_name: str, **kwargs):
        super().__init__(*children, **kwargs)
        self.callback_name = callback_name

    def action_select_current(self) -> None:
        owner = self.parent
        if owner is None or not hasattr(owner, "filtered") or not owner.filtered:
            return
        index = self.index if self.index is not None else 0
        if 0 <= index < len(owner.filtered):
            getattr(owner.app, self.callback_name)(owner.filtered[index][1])


class SearchPanel(Vertical):
    BINDINGS = [Binding("escape", "close_panel", "Close", show=False)]
    DEFAULT_CSS = """
    SearchPanel { width: 1fr; height: 1fr; }
    SearchPanel .title { text-style: bold; color: $accent; height: auto; }
    SearchPanel .hint { color: $text-muted; margin: 1 0; height: auto; }
    SearchPanel .search { margin-bottom: 1; }
    SearchPanel .list { height: 1fr; border: round $surface; }
    SearchPanel ListItem { padding: 0 1; }
    SearchPanel .actions { height: 3; margin-top: 1; }
    SearchPanel .actions Button { width: 1fr; }
    """

    def __init__(self, title: str, items: list[tuple[str, str]], *, callback_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.title_text = title
        self.items = list(items)
        self.filtered = self.items[:]
        self.callback_name = callback_name

    def compose(self) -> ComposeResult:
        yield Static(self.title_text, classes="title")
        yield Static("Type to search · ↓ focus list · ↑/↓ move · Enter select · Esc close", classes="hint")
        yield SearchInput(placeholder="Search…", classes="search", id=f"{self.id}_search", target_id=f"{self.id}_list")
        yield SelectList(id=f"{self.id}_list", classes="list", callback_name=self.callback_name)
        with Horizontal(classes="actions"):
            yield Button("Cancel", id=f"{self.id}_cancel")

    def action_close_panel(self) -> None:
        self.app.close_setup_overlay()

    def on_mount(self) -> None:
        self.refresh_items()
        self.query_one(f"#{self.id}_search", Input).focus()

    def refresh_items(self) -> None:
        view = self.query_one(f"#{self.id}_list", ListView)
        view.clear()
        for label, _value in self.filtered:
            view.append(ListItem(Static(label)))
        if not self.filtered:
            view.append(ListItem(Static("No matches")))

    def set_items(self, items: list[tuple[str, str]]) -> None:
        self.items = list(items)
        self.filtered = self.items[:]
        if self.is_attached:
            search = self.query_one(f"#{self.id}_search", Input)
            search.value = ""
            self.refresh_items()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != f"{self.id}_search":
            return
        query = event.value.strip().lower()
        self.filtered = [item for item in self.items if query in item[0].lower() or query in item[1].lower()]
        self.refresh_items()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == f"{self.id}_search" and len(self.filtered) == 1:
            getattr(self.app, self.callback_name)(self.filtered[0][1])

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        index = event.list_view.index
        if index is not None and 0 <= index < len(self.filtered):
            getattr(self.app, self.callback_name)(self.filtered[index][1])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == f"{self.id}_cancel":
            self.app.close_setup_overlay()


class ProviderPicker(SearchPanel):
    def __init__(self, providers: list[str]) -> None:
        super().__init__("PROVIDER · Search", [(name, name) for name in providers], callback_name="_provider_selected", id="provider_picker")


class ModelPicker(SearchPanel):
    def __init__(self) -> None:
        super().__init__("MODEL · Live catalog", [], callback_name="_model_selected", id="model_picker")

    def set_models(self, models: list[ModelInfo]) -> None:
        items = []
        for model in models:
            caps = ", ".join(sorted(model.capabilities))
            free = "  ·  FREE" if model.id.lower() == "openrouter/free" or model.id.lower().endswith(":free") else ""
            label = f"{model.id}{free}  ·  {caps}" if caps else f"{model.id}{free}"
            items.append((label, model.id))
        self.set_items(items)


class ApiKeyPanel(Vertical):
    DEFAULT_CSS = """
    ApiKeyPanel { width: 1fr; height: 1fr; }
    ApiKeyPanel .title { text-style: bold; color: $accent; height: auto; }
    ApiKeyPanel .hint { color: $text-muted; margin: 1 0; height: auto; }
    ApiKeyPanel #setup_key { margin: 1 0; }
    ApiKeyPanel .actions { height: 3; }
    ApiKeyPanel .actions Button { width: 1fr; }
    """

    def __init__(self) -> None:
        super().__init__(id="api_key_panel")
        self.provider = "provider"

    def compose(self) -> ComposeResult:
        yield Static("CONNECT", classes="title", id="key_title")
        yield Static("API key is memory-only for this session. Enter sends the key and immediately loads the provider's live model catalog.", classes="hint")
        yield Input(placeholder="API key", password=True, id="setup_key")
        with Horizontal(classes="actions"):
            yield Button("Load models", id="key_continue", variant="primary")
            yield Button("Use environment / local", id="key_skip")
            yield Button("Back", id="key_back")

    def on_mount(self) -> None:
        self.query_one("#setup_key", Input).focus()

    def set_provider(self, provider: str) -> None:
        self.provider = provider
        if self.is_attached:
            self.query_one("#key_title", Static).update(f"CONNECT · {provider}")
            self.query_one("#setup_key", Input).value = ""
            self.query_one("#setup_key", Input).focus()

    def submit(self) -> None:
        key = self.query_one("#setup_key", Input).value
        self.app.run_worker(self.app._api_key_submitted(key), exclusive=True, name="model-discovery")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "setup_key":
            self.submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "key_continue":
            self.submit()
        elif event.button.id == "key_skip":
            self.query_one("#setup_key", Input).value = ""
            self.submit()
        elif event.button.id == "key_back":
            self.app.open_provider_screen()
