# KRBI Tools

Tools extend KRBI Agent with controlled actions while keeping the chat transcript readable.

## Safe tools

- `clock` — current local and UTC time.
- `system_info` — runtime and platform details.
- `read_file` — read a workspace text file.
- `list_dir` — list a workspace directory.
- `search_files` — find workspace files and optionally search their text.
- `file_exists` — inspect whether a workspace path exists.

## Approval-gated tools

- `write_file` — write text inside the workspace.
- `shell` — run a command inside the workspace.

## What happens during a tool call

The model requests a function, KRBI validates the request, runs the tool when allowed, and sends the result back to the model. The result is not copied into the chat transcript as a raw dump. The UI may show only a brief completion status.

## Workspace boundary

File tools reject paths that escape the configured workspace. Shell commands run with the workspace as their working directory and are time-limited.

## Approval

Use Settings or the approval commands to decide which dangerous tools are allowed.
