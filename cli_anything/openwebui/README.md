# cli-anything-openwebui

CLI-Anything harness for OpenWebUI. It operates a running OpenWebUI backend through the real FastAPI HTTP API.

## Install

```bash
pip install git+https://github.com/ashaiful/cli-anything-openwebui.git
```

OpenWebUI itself must be running separately:

```bash
open-webui serve
```

Pass a deployment URL with `--base-url` if it is not running at `http://localhost:8080`.

You can also configure a deployment with environment variables:

```bash
export OPENWEBUI_BASE_URL=https://your-openwebui.example.com
export OPENWEBUI_TOKEN=your-api-key-or-bearer-token
```

`OPENWEBUI_URL` is accepted as an alias for `OPENWEBUI_BASE_URL`, and `OPENWEBUI_API_KEY` is accepted as an alias for `OPENWEBUI_TOKEN`.

## Basic Usage

```bash
cli-anything-openwebui --base-url http://localhost:8080 server status
cli-anything-openwebui --json config show
cli-anything-openwebui auth signin --email you@example.com --password '...'
cli-anything-openwebui --json models list
cli-anything-openwebui --json chats list
cli-anything-openwebui --json memories list
cli-anything-openwebui --json prompts list
cli-anything-openwebui --json notes search --query runbook
cli-anything-openwebui --json automations list
cli-anything-openwebui chats select <chat-id>
cli-anything-openwebui session undo
```

Run `cli-anything-openwebui` with no subcommand to enter the REPL.

## Command Groups

- `server`: status, OpenAPI schema, version.
- `auth`: signin, signup, signout, current user, API key commands.
- `models`: list, show, tags, base, export, sync.
- `memories`: list, add, query, update, delete, reset, clear.
- `prompts`: list, show, tags, create, update, metadata update, version selection, toggle, delete, history list/show/diff/delete.
- `notes`: list, pinned list, search, show, create, update, access set, pin toggle, delete.
- `automations`: list, show, create, update, toggle, run, delete, runs.
- `chats`: list, show, create, update, delete, pin, archive, clone, share, select, tag add/remove.
- `files`: list, show, upload, delete, content.
- `users`: list, all, search, me.
- `api`: generic get, post, delete for endpoints not wrapped yet.
- `session`: status, select, undo, redo.
- `config`: show, save.

## JSON Mode

Every command supports root-level `--json` for machine-readable output:

```bash
cli-anything-openwebui --json api get /api/v1/models/tags
```

## Tests

```bash
pip install -e .[test]
python -m pytest cli_anything/openwebui/tests -v
```

For installed-command validation:

```bash
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest cli_anything/openwebui/tests -v -s
```
