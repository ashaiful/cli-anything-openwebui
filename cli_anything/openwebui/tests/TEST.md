# OpenWebUI CLI-Anything Test Plan

## Test Inventory Plan

- `test_core.py`: 16 unit tests planned for session state, HTTP request preparation, JSON parsing, error handling, token storage, and first-class OpenWebUI wrapper endpoint mapping.
- `test_full_e2e.py`: 15 subprocess tests planned for installed CLI help, JSON/YAML config output, environment/profile configuration, generic API calls, auth login state persistence, chat/RAG/admin workflows, stable error exits, and first-class memories/prompts/notes/automations workflows.

## Unit Test Plan

### `core.session`

- `SessionState.empty()` creates a default session with no token or selected chat.
- `SessionState.select_chat()` records undo history and updates `current_chat_id`.
- `SessionState.undo()` restores the previous selected chat and records redo history.
- `SessionState.redo()` reapplies the undone selected chat.

Expected tests: 4.

### `utils.openwebui_backend`

- `OpenWebUIClient` sends bearer tokens in the `Authorization` header.
- `OpenWebUIClient` parses JSON responses and handles empty 204 responses.
- HTTP errors raise a `RuntimeError` with method, endpoint, status code, and response text.
- Invalid JSON responses return a structured text payload instead of crashing.

Expected tests: 4.

### `core.memories`

- `list_memories()` maps to `GET /api/v1/memories/`.
- `add_memory()`, `query_memories()`, and `update_memory()` send the exact backend JSON bodies.
- `delete_memory()`, `reset_memories()`, and `clear_memories()` target the current-user backend endpoints.

Expected tests: covered by 1 grouped endpoint-mapping test.

### `core.notes`

- `list_notes()` and `search_notes()` send expected query params.
- `create_note()`, `update_note()`, and `update_note_access()` preserve data/meta/access-grant JSON payloads.
- `pin_note()` and `delete_note()` target the backend toggle/delete endpoints.

Expected tests: covered by 1 grouped endpoint-mapping test.

### `core.prompts`

- `list_prompts()`, `tags()`, and `show_prompt()` map to prompt library read endpoints.
- `create_prompt()`, `update_prompt()`, `update_prompt_metadata()`, and `set_prompt_version()` preserve backend payload shapes.
- Prompt history list/diff/delete commands map to the nested history endpoints.

Expected tests: covered by 1 grouped endpoint-mapping test.

### `core.automations`

- `list_automations()`, `show_automation()`, and `list_automation_runs()` send expected query params.
- `create_automation()`, `update_automation()`, `toggle_automation()`, `run_automation()`, and `delete_automation()` map to the automation backend endpoints.

Expected tests: covered by 1 grouped endpoint-mapping test.

## E2E Test Plan

### CLI subprocess tests

- `cli-anything-openwebui --help` works from any current working directory.
- `cli-anything-openwebui --json config show` prints parseable JSON with connection state and masks tokens.
- `OPENWEBUI_BASE_URL` plus `OPENWEBUI_TOKEN` can configure the CLI without flags.
- `cli-anything-openwebui --json api get /api/v1/models/tags` can call a small OpenWebUI-like HTTP server and return its JSON response.
- `cli-anything-openwebui --json --config <file> auth signin ...` persists the returned token and user identity in the session config.
- `cli-anything-openwebui --json memories ...` can list, add, query, update, delete, reset, and clear current-user memories.
- `cli-anything-openwebui --json notes ...` can list, search, create, update, set access grants, pin, and delete notes.
- `cli-anything-openwebui --json prompts ...` can list, tag, show, create, update metadata, select a version, toggle, inspect history, diff history, and delete prompts/history rows.
- `cli-anything-openwebui --json automations ...` can list, show, create, update, toggle, run, inspect runs, and delete automations.

These tests exercise the installed console script via `_resolve_cli("cli-anything-openwebui")`; the helper falls back to `python -m cli_anything.openwebui.openwebui_cli` for local development unless `CLI_ANYTHING_FORCE_INSTALLED=1` is set.

## Realistic Workflow Scenarios

### Inspect A Running OpenWebUI Instance

- Simulates: an agent connecting to an existing OpenWebUI deployment before making changes.
- Operations chained: show config, check server status, list models, list chats.
- Verified: JSON output is parseable and server responses are returned without shape loss.

### Authenticate And Persist Session

- Simulates: an agent signing in once, then reusing a saved bearer token for later commands.
- Operations chained: signin, save token, show config, call an authenticated endpoint.
- Verified: token is stored in the harness config, displayed masked, and sent as `Authorization: Bearer ...`.

### Chat Workspace Management

- Simulates: an agent inspecting and organizing user chats.
- Operations chained: list chats, select a current chat, pin or archive a chat, undo local selection changes.
- Verified: command payloads map directly to OpenWebUI REST endpoints and local selection undo/redo behaves deterministically.

### Agent Workspace Knowledge Management

- Simulates: an agent managing OpenWebUI persistent working context.
- Operations chained: query memories, inspect prompt library, search notes, and list active automations.
- Verified: command payloads map directly to OpenWebUI REST endpoints and JSON responses preserve server shapes, including raw vector-search results and boolean delete responses.

## Backend Validation Notes

The first automated E2E layer uses a minimal OpenWebUI-like HTTP server so the harness can be validated without mutating a user's real deployment. True backend validation should be run manually against a live OpenWebUI server with:

```bash
cli-anything-openwebui --base-url http://localhost:8080 server status
cli-anything-openwebui --base-url http://localhost:8080 auth signin --email "$OPENWEBUI_EMAIL" --password "$OPENWEBUI_PASSWORD"
cli-anything-openwebui --base-url http://localhost:8080 --json models list
```

## Test Results

Source-mode run:

```text
...............................                                          [100%]
31 passed in 37.85s
```

Installed-command run:

```text
[_resolve_cli] Using installed command: cli-anything-openwebui
...............................
31 passed in 37.89s
```

## Summary Statistics

- Total tests: 31
- Pass rate: 100%
- Source-mode command: `python -m pytest cli_anything\openwebui\tests -q`
- Installed-command command: `$env:CLI_ANYTHING_FORCE_INSTALLED='1'; python -m pytest cli_anything\openwebui\tests -q -s`

## Coverage Notes

The automated suite verifies session behavior, HTTP client behavior, JSON output, local config masking, generic API calls, signin persistence, memories/prompts/notes/automations endpoint mapping, and the installed console script. It does not start a full OpenWebUI server or mutate a real deployment; run the backend validation commands above against a live instance for deployment-specific verification. The current test environment emits a `pytest-asyncio` fixture-scope deprecation warning that is unrelated to the harness behavior.
