# How KRBI Agent Works

KRBI Agent is organized around one simple flow: connect a provider, choose a model, send a message, and let the agent coordinate the response and any approved tools.

## The main pieces

**Provider layer** talks to remote APIs and local model servers. Providers expose model discovery and streaming chat through one common interface.

**Agent layer** keeps conversation history, sends messages to the selected model, collects streaming text, handles function calls, and feeds tool results back to the model when another round is needed.

**Tool layer** describes available functions and enforces workspace boundaries and approval rules. Tool results are internal agent data rather than chat decoration.

**Storage layer** keeps saved conversations as Markdown files in `~/.krbi/chats/`.

**TUI layer** provides the terminal experience, including provider/model pickers, Settings, command search, and the scrolling conversation view.

**Web layer** provides the browser/mobile experience with the same provider and model workflow.

**Updater** reads `update.txt`, checks the GitHub source, fast-forwards a local checkout when the code is newer, and restarts the application.

## Safety boundary

Read-only workspace tools can run automatically. Mutating operations such as writing files or running shell commands are approval-gated. Workspace paths are resolved and rejected when they escape the configured workspace.

## User-visible rule

The chat view is for the conversation. Setup controls, credentials, tool internals, and update progress belong in dedicated UI surfaces so the transcript remains readable.
