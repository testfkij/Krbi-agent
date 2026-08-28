# Configure KRBI Agent

KRBI keeps durable settings in `~/.krbi/settings.toml` and provider configuration in `~/.krbi/config.toml`. API keys entered in the UI are session-scoped.

## First run

Start KRBI, open Provider, choose a provider, enter its key when required, and let KRBI load the live model list. Select a model and return to chat.

## Defaults

The default provider and model can be remembered by the application. Local providers can be selected without a remote key when their local endpoint is available.

## Approval modes

`default` keeps mutating tools behind approval. `auto_edit` allows approved editing behavior while keeping shell execution gated. `plan` keeps work in a read-only planning style. `yolo` removes per-tool dangerous-operation gating and should only be used deliberately.

## Banner

The banner text is stored in settings and can be changed from the TUI Settings screen or `/banner`.

## Session data

Saved chats live in `~/.krbi/chats/`. Reset clears active session state while keeping saved chats.
