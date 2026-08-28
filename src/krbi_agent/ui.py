from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, ListItem, ListView, Static


class PickerListView(ListView):
    BINDINGS = [Binding("enter", "choose", "Select", show=False)]

    def action_choose(self) -> None:
        index = self.index
        if index is not None and hasattr(self.app, "filtered") and 0 <= index < len(self.app.filtered):
            self.app.exit(self.app.filtered[index])


class Picker(App[str]):
    TITLE = "KRBI Agent"
    SUB_TITLE = "selection"
    CSS = """
    Screen { align: center middle; background: $background; }
    #panel { width: 82; height: auto; max-height: 82%; padding: 1 2; border: round $accent; background: $panel; }
    #title { text-style: bold; color: $accent; }
    #hint { color: $text-muted; margin: 1 0; }
    #search { margin-bottom: 1; }
    #list { height: auto; max-height: 18; border: round $surface; }
    ListItem { padding: 0 1; }
    Footer { height: 1; }
    """
    BINDINGS = [Binding("escape", "cancel", "Back"), Binding("ctrl+q", "cancel", "Back")]

    def __init__(self, title: str, options: list[str]) -> None:
        super().__init__()
        self.title_text = title
        self.options = list(dict.fromkeys(options))
        self.filtered = self.options[:]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="panel"):
            yield Static(self.title_text, id="title")
            yield Static("Type to filter · ↑/↓ move · Enter select · Esc back", id="hint")
            yield Input(placeholder="Filter…", id="search")
            yield PickerListView(*[ListItem(Static(value)) for value in self.filtered], id="list")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#search", Input).focus()
        if self.filtered:
            self.query_one("#list", ListView).focus()

    def _render_options(self) -> None:
        view = self.query_one("#list", PickerListView)
        view.clear()
        view.extend(ListItem(Static(value)) for value in self.filtered)
        if self.filtered:
            view.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search" and len(self.filtered) == 1:
            self.exit(self.filtered[0])

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search":
            return
        query = event.value.strip().lower()
        self.filtered = [value for value in self.options if query in value.lower()]
        self._render_options()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        index = event.list_view.index
        if index is not None and 0 <= index < len(self.filtered):
            self.exit(self.filtered[index])

    def action_cancel(self) -> None:
        self.exit("")


def pick(title: str, options: list[str]) -> str:
    if not options:
        raise ValueError("No selectable options")
    return Picker(title, options).run() or options[0]
