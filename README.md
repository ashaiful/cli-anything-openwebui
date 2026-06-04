# cli-anything-openwebui

CLI-Anything harness for operating a running OpenWebUI backend from the command line.

This package exposes an agent-friendly CLI for OpenWebUI's real HTTP API. It does not bundle or reimplement OpenWebUI; you connect it to an OpenWebUI server that is already running locally or on a deployment URL.

## Install

Install directly from GitHub:

```bash
pip install git+https://github.com/ashaiful/cli-anything-openwebui.git
```

Verify the command is available:

```bash
cli-anything-openwebui --help
```

## OpenWebUI Setup

Start OpenWebUI separately. For a local installation, one common option is:

```bash
open-webui serve
```

The CLI defaults to `http://localhost:8080`. Use `--base-url` or environment variables for a different deployment:

```bash
export OPENWEBUI_BASE_URL=https://your-openwebui.example.com
export OPENWEBUI_TOKEN=your-api-key-or-bearer-token
```

`OPENWEBUI_URL` is accepted as an alias for `OPENWEBUI_BASE_URL`, and `OPENWEBUI_API_KEY` is accepted as an alias for `OPENWEBUI_TOKEN`.

## First Commands

Check the server:

```bash
cli-anything-openwebui --base-url http://localhost:8080 server status
```

Sign in and persist a local session token:

```bash
cli-anything-openwebui auth signin --email you@example.com --password '...'
```

Use JSON output for agent workflows:

```bash
cli-anything-openwebui --json models list
cli-anything-openwebui --json chats list
cli-anything-openwebui --json memories list
cli-anything-openwebui --json prompts list
cli-anything-openwebui --json notes search --query runbook
cli-anything-openwebui --json automations list
```

Run without a subcommand to enter the interactive REPL:

```bash
cli-anything-openwebui
```

## Command Groups

- `server`: status, OpenAPI schema, version.
- `profile`: saved deployment profiles with optional keyring token storage.
- `auth`: signin, signup, current user, token inspection, refresh, API key management, and signout.
- `chat`: send a completion request with prompt/stdin, system prompt, chat id, file context, collection context, and sampling options.
- `rag`: knowledge collection list/create/delete, file add/remove, and collection search.
- `models`: list, show, tags, base models, export, and sync.
- `chats`: list, show, create, update, delete, pin, archive, clone, share, select, and tag management.
- `files`: list, show, upload, delete, and content retrieval.
- `users`: current user and admin-oriented list/search helpers.
- `admin`: admin stats, users, and config inspection.
- `memories`: list, add, query, update, delete, reset, and clear.
- `prompts`: list, show, tags, create, update, metadata update, version restore, toggle, delete, and history commands.
- `notes`: list, pinned list, search, show, create, update, access grants, pin toggle, and delete.
- `automations`: list, show, create, update, toggle, run, delete, and run history.
- `api`: generic GET/POST/DELETE escape hatch for endpoints not wrapped yet.
- `session`: local state, selected chat, undo, and redo.
- `config`: connection configuration.

## Local State

The CLI stores local session state in `~/.cli-anything-openwebui/session.json` by default. It persists the base URL, bearer token, profiles, last user, current chat selection, and local undo/redo stacks.

Use `--keyring` with `auth signin` or `profile set` on supported systems to store profile/auth tokens in the OS keyring instead of the session JSON. Undo/redo applies to local harness state only; OpenWebUI server data remains the source of truth.

## Development

Clone the repository and install in editable mode:

```bash
git clone https://github.com/ashaiful/cli-anything-openwebui.git
cd cli-anything-openwebui
pip install -e .[test]
```

Run tests:

```bash
python -m pytest cli_anything/openwebui/tests -q
```

Validate the installed console script:

```bash
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest cli_anything/openwebui/tests -q -s
```

## CLI-AnythingHub Registry

This package is intended for the standalone repository path in CLI-AnythingHub. The registry entry is included in `registry-entry.json`.
