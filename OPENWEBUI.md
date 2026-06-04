# OpenWebUI CLI-Anything Harness

## Backend

OpenWebUI is a Svelte frontend over a FastAPI backend. The harness uses the real OpenWebUI HTTP API exposed by a running `open-webui` server. It does not reimplement chat, model, file, user, or auth behavior.

Default base URL: `http://localhost:8080`.

## Command Groups

- `server`: health, version, and OpenAPI inspection.
- `profile`: saved deployment profiles with optional system keyring token storage.
- `auth`: signin, signup, current user, token inspection/refresh, API key management, and signout.
- `chat`: send a completion request with prompt/stdin, system prompt, chat id, file/collection context, and sampling options.
- `rag`: knowledge collection list/create/delete, file add/remove, and collection search.
- `memories`: current-user memory list/add/query/update/delete, vector reset, and full memory clear.
- `prompts`: prompt library list/show/tags/create/update, metadata update, version restore, toggle/delete, and history list/show/diff/delete.
- `notes`: note list/pinned/search/show/create/update, access grants, pin toggle, and delete.
- `automations`: scheduled automation list/show/create/update/toggle/run/delete and run history.
- `admin`: admin stats, users, and config inspection.
- `models`: list, show, tags, base models, export, and sync.
- `chats`: list, show, create, update from JSON, delete, pin, archive, clone, share, tag management, and local selection.
- `files`: list, show, upload, delete, and content retrieval.
- `users`: current user and admin-oriented list/search helpers.
- `api`: generic GET/POST/DELETE escape hatch for endpoints not wrapped yet.
- `session`: local state, selected chat, undo, and redo.
- `config`: connection configuration.

Output formats: text, JSON (`--json` or `--format json`), and YAML (`--format yaml`).

## State Model

The harness stores local state in JSON:

- `base_url`
- bearer `token`
- named `profiles`
- `default_profile`
- `current_chat_id`
- `last_user`
- undo/redo stacks for local session state

On supported systems, `auth signin --keyring` and `profile set --keyring` can store tokens in the OS keyring instead of the session JSON.

## Exit Codes

- `0`: success
- `1`: generic CLI/runtime error
- `3`: authentication or authorization failure
- `4`: connection or timeout failure
- `5`: OpenWebUI server-side failure

OpenWebUI server-side data remains the source of truth. Undo/redo applies to local harness state, not remote data mutations.

## Limitations

The harness requires a running OpenWebUI server for backend operations. Automated tests include an OpenWebUI-like HTTP service for deterministic CLI validation; true backend validation should be run against a live server before depending on a deployment-specific workflow.
