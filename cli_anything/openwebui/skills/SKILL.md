---
name: cli-anything-openwebui
description: Operate a running OpenWebUI backend through an agent-friendly CLI with JSON/YAML output, profiles, auth/session state, chat/RAG/model/file/user/admin, memories, prompts, notes, automation commands, and a generic API escape hatch.
---

# cli-anything-openwebui

Use this skill when you need to inspect or operate OpenWebUI from the command line.

## Requirements

- Install with `pip install git+https://github.com/ashaiful/cli-anything-openwebui.git`.
- Run OpenWebUI separately with `open-webui serve`, or pass `--base-url` for an existing deployment.
- For existing deployments, prefer `OPENWEBUI_BASE_URL` plus either `OPENWEBUI_TOKEN`, a saved profile, or a saved `auth signin` session.
- Use `--json` or `--format yaml` for machine-readable output.

## Common Commands

```bash
cli-anything-openwebui --json config show
cli-anything-openwebui --format yaml config show
cli-anything-openwebui --base-url http://localhost:8080 server status
cli-anything-openwebui auth signin --email you@example.com --password '...'
cli-anything-openwebui profile set prod --base-url https://openwebui.example.com --token '...' --default
cli-anything-openwebui --profile prod --json models list
cli-anything-openwebui chat send --model gpt-4.1 --prompt 'Summarize the deployment' --no-stream
cli-anything-openwebui --json rag collections list
cli-anything-openwebui --json rag search --collection <collection-id> --query 'runtime config'
cli-anything-openwebui --json admin users
cli-anything-openwebui --json auth me
cli-anything-openwebui --json models list
cli-anything-openwebui --json chats list
cli-anything-openwebui --json memories query --content 'preferred answer style' --top-k 3
cli-anything-openwebui --json prompts list --query summarize
cli-anything-openwebui --json notes search --query runbook
cli-anything-openwebui --json automations list --status active
cli-anything-openwebui chats select <chat-id>
cli-anything-openwebui session undo
cli-anything-openwebui --json files list
```

## Environment Variables

- `OPENWEBUI_BASE_URL`: OpenWebUI deployment URL, for example `https://openwebui.example.com`.
- `OPENWEBUI_URL`: alias for `OPENWEBUI_BASE_URL`.
- `OPENWEBUI_TOKEN`: bearer token or OpenWebUI API key.
- `OPENWEBUI_API_KEY`: alias for `OPENWEBUI_TOKEN`.
- `OPENWEBUI_PROFILE`: saved profile name to use by default.

## Command Groups

- `server status|openapi|version`
- `profile list|set|delete|use`
- `auth signin|signup|me|signout|token|refresh|api-key create|get|delete`
- `chat send`
- `rag collections list|create|delete|add-file|remove-file`
- `rag search`
- `memories list|add|query|update|delete|reset|clear`
- `prompts list|show|tags|create|update|update-meta|version|toggle|delete|history list|history show|history diff|history delete`
- `notes list|search|show|create|update|access set|pin|delete`
- `automations list|show|create|update|toggle|run|delete|runs`
- `admin stats|users|config`
- `models list|show|tags|base|export|sync`
- `chats list|show|create|update|delete|pin|archive|clone|share|select|tag add|tag remove`
- `files list|show|upload|delete|content`
- `users list|all|search|me`
- `api get|post|delete`
- `session status|select|undo|redo`
- `config show|save`

## Generic API Access

Use the `api` group for endpoints not yet wrapped:

```bash
cli-anything-openwebui --json api get /api/v1/models/tags
cli-anything-openwebui --json api post /api/v1/retrieval/process/text --data '{"content":"hello"}'
```

## Exit Codes

- `0`: success
- `1`: generic CLI/runtime error
- `3`: authentication or authorization failure
- `4`: connection or timeout failure
- `5`: OpenWebUI server-side failure

## State

The CLI stores local session state in `~/.cli-anything-openwebui/session.json` by default. It persists the base URL, bearer token, profiles, last user, current chat selection, and local undo/redo stacks. Use `--keyring` on supported systems to store profile/auth tokens in the OS keyring instead of the session JSON. Undo/redo applies to local harness state only.
