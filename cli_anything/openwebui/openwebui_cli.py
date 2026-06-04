import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any

import click

from cli_anything.openwebui.core import admin as admin_core
from cli_anything.openwebui.core import auth as auth_core
from cli_anything.openwebui.core import automations as automations_core
from cli_anything.openwebui.core import chat as chat_core
from cli_anything.openwebui.core import chats as chats_core
from cli_anything.openwebui.core import files as files_core
from cli_anything.openwebui.core import memories as memories_core
from cli_anything.openwebui.core import models as models_core
from cli_anything.openwebui.core import notes as notes_core
from cli_anything.openwebui.core import prompts as prompts_core
from cli_anything.openwebui.core import rag as rag_core
from cli_anything.openwebui.core import server as server_core
from cli_anything.openwebui.core import users as users_core
from cli_anything.openwebui.core.session import SessionState, default_config_path
from cli_anything.openwebui.utils import token_store
from cli_anything.openwebui.utils.openwebui_backend import OpenWebUIClient
from cli_anything.openwebui.utils.repl_skin import ReplSkin


CONTEXT_SETTINGS = {'help_option_names': ['-h', '--help']}
_output_format = 'text'


EXIT_GENERIC = 1
EXIT_AUTH = 3
EXIT_NETWORK = 4
EXIT_SERVER = 5


def output(data: Any, as_json: bool) -> None:
    if as_json or _output_format == 'json':
        click.echo(json.dumps(data, indent=2, default=str))
        return
    if _output_format == 'yaml':
        import yaml

        click.echo(yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip())
        return
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                click.echo(f'{key}: {json.dumps(value, default=str)}')
            else:
                click.echo(f'{key}: {value}')
    elif isinstance(data, list):
        for item in data:
            click.echo(json.dumps(item, default=str) if isinstance(item, dict) else str(item))
    else:
        click.echo(str(data))


def load_json_value(data: str | None, data_file: str | None) -> Any:
    if data_file:
        return json.loads(Path(data_file).read_text(encoding='utf-8'))
    if data:
        return json.loads(data)
    return {}


def load_optional_json_value(data: str | None, data_file: str | None, default: Any) -> Any:
    if data or data_file:
        return load_json_value(data, data_file)
    return default


def load_text_value(text: str | None, text_file: str | None) -> str | None:
    if text_file:
        return Path(text_file).read_text(encoding='utf-8')
    return text


def require_list(value: Any, label: str) -> list:
    if not isinstance(value, list):
        raise RuntimeError(f'{label} must be a JSON array')
    return value


def client_from_ctx(ctx: click.Context) -> OpenWebUIClient:
    state: SessionState = ctx.obj['state']
    return OpenWebUIClient(state.base_url, token=state.token, timeout=ctx.obj.get('timeout') or 30)


def save_state(ctx: click.Context) -> Path:
    state: SessionState = ctx.obj['state']
    return state.save(ctx.obj['config_path'])


def command_guard(func):
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context(silent=True)
        as_json = bool(ctx and ctx.obj and ctx.obj.get('as_json'))
        try:
            return func(*args, **kwargs)
        except RuntimeError as exc:
            exit_code = classify_exit_code(exc)
            if as_json:
                click.echo(json.dumps({'error': str(exc), 'type': 'RuntimeError', 'exit_code': exit_code}, indent=2))
            else:
                click.echo(f'Error: {exc}', err=True)
            raise click.exceptions.Exit(exit_code)

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def classify_exit_code(exc: RuntimeError) -> int:
    message = str(exc).lower()
    if 'api error 401' in message or 'api error 403' in message or 'unauthorized' in message or 'forbidden' in message:
        return EXIT_AUTH
    if 'cannot connect' in message or 'timed out' in message or 'connection' in message:
        return EXIT_NETWORK
    for status_code in ('api error 500', 'api error 502', 'api error 503', 'api error 504'):
        if status_code in message:
            return EXIT_SERVER
    return EXIT_GENERIC


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option('--base-url', default=None, help='OpenWebUI server URL (default: http://localhost:8080)')
@click.option('--token', default=None, help='Bearer token or API key for OpenWebUI')
@click.option('--config', 'config_path', type=click.Path(), default=None, help='Harness session config path')
@click.option('--profile', default=None, help='Named OpenWebUI deployment profile')
@click.option('--format', 'output_format', type=click.Choice(['text', 'json', 'yaml']), default=None, help='Output format')
@click.option('--json', 'as_json', is_flag=True, default=False, help='Output as JSON')
@click.option('--timeout', default=30, type=int, help='Request timeout in seconds')
@click.pass_context
def cli(
    ctx: click.Context,
    base_url: str | None,
    token: str | None,
    config_path: str | None,
    profile: str | None,
    output_format: str | None,
    as_json: bool,
    timeout: int,
):
    """OpenWebUI CLI-Anything harness for a running OpenWebUI backend."""
    global _output_format
    ctx.ensure_object(dict)
    resolved_config = Path(config_path) if config_path else default_config_path()
    state = SessionState.load(resolved_config)
    effective_profile = profile or os.environ.get('OPENWEBUI_PROFILE') or state.default_profile
    state.apply_profile(effective_profile)
    env_base_url = os.environ.get('OPENWEBUI_BASE_URL') or os.environ.get('OPENWEBUI_URL')
    env_token = os.environ.get('OPENWEBUI_TOKEN') or os.environ.get('OPENWEBUI_API_KEY')
    state.base_url = base_url or env_base_url or state.base_url
    state.token = token or env_token or state.token
    if not state.token and effective_profile:
        state.token = token_store.get_token(effective_profile, state.base_url)
    _output_format = 'json' if as_json else (output_format or 'text')
    ctx.obj.update(
        {
            'state': state,
            'config_path': resolved_config,
            'as_json': as_json,
            'profile': effective_profile,
            'timeout': timeout,
        }
    )
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


def main():
    cli(obj={})


@cli.command(hidden=True)
@click.pass_context
def repl(ctx: click.Context):
    """Start interactive REPL mode."""
    skin = ReplSkin('openwebui', version='1.0.0')
    skin.print_banner()
    skin.info(f'OpenWebUI: {ctx.obj["state"].base_url}')
    pt_session = skin.create_prompt_session()
    commands = {
        'server status|openapi|version': 'Inspect backend health and metadata',
        'auth signin|signup|me|api-key|signout': 'Authentication and API keys',
        'chat send': 'Send chat completions',
        'models list|show|tags|base|export|sync': 'Model workspace commands',
        'rag collections|search': 'Knowledge and retrieval commands',
        'memories list|add|query|update|delete|reset|clear': 'User memory commands',
        'notes list|search|show|create|update|access|pin|delete': 'Notebook commands',
        'prompts list|show|tags|create|update|history': 'Prompt library commands',
        'automations list|show|create|update|toggle|run|delete|runs': 'Automation commands',
        'admin stats|users|config': 'Admin inspection commands',
        'profile list|set|delete|use': 'Deployment profiles',
        'chats list|show|create|update|delete|pin|archive|clone|share|tag|select': 'Chat workspace commands',
        'files list|show|upload|delete|content': 'File workspace commands',
        'users list|all|search|me': 'User inspection commands',
        'api get|post|delete': 'Generic endpoint access',
        'session status|select|undo|redo': 'Local harness state',
        'config show|save': 'Connection config',
    }
    while True:
        try:
            state: SessionState = ctx.obj['state']
            line = skin.get_input(pt_session, project_name=state.current_chat_id or '')
            if not line:
                continue
            if line.lower() in ('quit', 'exit', 'q'):
                break
            if line.lower() == 'help':
                skin.help(commands)
                continue
            args = shlex.split(line)
            cli.main(args=args, obj=dict(ctx.obj), standalone_mode=False)
        except (EOFError, KeyboardInterrupt):
            break
        except click.exceptions.UsageError as exc:
            skin.error(str(exc))
        except RuntimeError as exc:
            skin.error(str(exc))
        except SystemExit:
            pass
    skin.print_goodbye()


@cli.group()
@click.pass_context
def config(ctx: click.Context):
    """Connection configuration."""


@config.command('show')
@click.pass_context
def config_show(ctx: click.Context):
    """Show current harness configuration."""
    output(ctx.obj['state'].masked(), ctx.obj['as_json'])


@config.command('save')
@click.pass_context
def config_save(ctx: click.Context):
    """Save current harness configuration."""
    path = save_state(ctx)
    output({'saved': str(path)}, ctx.obj['as_json'])


@cli.group()
@click.pass_context
def profile(ctx: click.Context):
    """Named deployment profiles."""


@profile.command('list')
@click.pass_context
def profile_list(ctx: click.Context):
    """List configured profiles."""
    state: SessionState = ctx.obj['state']
    output({'default_profile': state.default_profile, 'profiles': state.masked()['profiles']}, ctx.obj['as_json'])


@profile.command('set')
@click.argument('name')
@click.option('--base-url', default=None, help='OpenWebUI deployment URL')
@click.option('--token', default=None, help='Bearer token or API key')
@click.option('--default', 'make_default', is_flag=True, help='Make this the default profile')
@click.option('--keyring', 'store_keyring', is_flag=True, help='Store token in system keyring when available')
@click.pass_context
def profile_set(
    ctx: click.Context,
    name: str,
    base_url: str | None,
    token: str | None,
    make_default: bool,
    store_keyring: bool,
):
    """Create or update a deployment profile."""
    state: SessionState = ctx.obj['state']
    effective_base_url = base_url or state.base_url
    token_for_profile = token
    keyring_saved = False
    if token and store_keyring:
        keyring_saved = token_store.set_token(name, effective_base_url, token)
        if keyring_saved:
            token_for_profile = None
    state.set_profile(name, effective_base_url, token_for_profile, make_default)
    save_state(ctx)
    output({'profile': name, 'base_url': effective_base_url, 'default': state.default_profile == name, 'keyring_saved': keyring_saved}, ctx.obj['as_json'])


@profile.command('delete')
@click.argument('name')
@click.pass_context
def profile_delete(ctx: click.Context, name: str):
    """Delete a deployment profile."""
    state: SessionState = ctx.obj['state']
    deleted = state.delete_profile(name)
    save_state(ctx)
    output({'deleted': deleted, 'profile': name}, ctx.obj['as_json'])


@profile.command('use')
@click.argument('name')
@click.pass_context
def profile_use(ctx: click.Context, name: str):
    """Set the default deployment profile."""
    state: SessionState = ctx.obj['state']
    if name not in state.profiles:
        raise click.ClickException(f"Unknown profile: {name}")
    state.default_profile = name
    state.apply_profile(name)
    save_state(ctx)
    output({'default_profile': name, 'state': state.masked()}, ctx.obj['as_json'])


@cli.group()
@click.pass_context
def server(ctx: click.Context):
    """Server health and metadata."""


@server.command('status')
@click.pass_context
@command_guard
def server_status(ctx: click.Context):
    """Check connectivity to OpenWebUI."""
    output(server_core.status(client_from_ctx(ctx)), ctx.obj['as_json'])


@server.command('openapi')
@click.pass_context
@command_guard
def server_openapi(ctx: click.Context):
    """Fetch OpenWebUI OpenAPI schema."""
    output(server_core.openapi(client_from_ctx(ctx)), ctx.obj['as_json'])


@server.command('version')
@click.pass_context
@command_guard
def server_version(ctx: click.Context):
    """Fetch OpenWebUI version metadata."""
    output(server_core.version(client_from_ctx(ctx)), ctx.obj['as_json'])


@cli.group()
@click.pass_context
def auth(ctx: click.Context):
    """Authentication and API keys."""


@auth.command('signin')
@click.option('--email', required=True)
@click.option('--password', required=True)
@click.option('--keyring', 'store_keyring', is_flag=True, help='Store token in system keyring instead of session JSON')
@click.pass_context
@command_guard
def auth_signin(ctx: click.Context, email: str, password: str, store_keyring: bool):
    """Sign in and persist the returned bearer token."""
    state: SessionState = ctx.obj['state']
    result = auth_core.signin(client_from_ctx(ctx), email, password)
    token = result.get('token') or result.get('access_token')
    if token:
        stored_in_keyring = False
        if store_keyring:
            profile_name = ctx.obj.get('profile') or state.default_profile or 'default'
            stored_in_keyring = token_store.set_token(profile_name, state.base_url, token)
        state.remember_auth(
            None if stored_in_keyring else token,
            {k: result.get(k) for k in ('id', 'email', 'name', 'role') if k in result},
        )
        save_state(ctx)
    output(result, ctx.obj['as_json'])


@auth.command('signup')
@click.option('--name', required=True)
@click.option('--email', required=True)
@click.option('--password', required=True)
@click.pass_context
@command_guard
def auth_signup(ctx: click.Context, name: str, email: str, password: str):
    """Create an account and persist the returned bearer token."""
    state: SessionState = ctx.obj['state']
    result = auth_core.signup(client_from_ctx(ctx), name, email, password)
    token = result.get('token') or result.get('access_token')
    if token:
        state.remember_auth(token, {k: result.get(k) for k in ('id', 'email', 'name', 'role') if k in result})
        save_state(ctx)
    output(result, ctx.obj['as_json'])


@auth.command('me')
@click.pass_context
@command_guard
def auth_me(ctx: click.Context):
    """Show the authenticated user."""
    output(auth_core.me(client_from_ctx(ctx)), ctx.obj['as_json'])


@auth.command('signout')
@click.pass_context
def auth_signout(ctx: click.Context):
    """Clear local token state."""
    state: SessionState = ctx.obj['state']
    state.remember_auth(None, None)
    save_state(ctx)
    output({'signed_out': True}, ctx.obj['as_json'])


@auth.command('token')
@click.option('--show', is_flag=True, help='Show the full token')
@click.pass_context
def auth_token(ctx: click.Context, show: bool):
    """Show token information."""
    state: SessionState = ctx.obj['state']
    token = state.token
    if not token and ctx.obj.get('profile'):
        token = token_store.get_token(ctx.obj['profile'], state.base_url)
    if show:
        rendered = token
    elif token and len(token) > 12:
        rendered = f'{token[:8]}...{token[-4:]}'
    else:
        rendered = '***' if token else None
    output({'profile': ctx.obj.get('profile'), 'base_url': state.base_url, 'token': rendered}, ctx.obj['as_json'])


@auth.command('refresh')
@click.pass_context
@command_guard
def auth_refresh(ctx: click.Context):
    """Refresh the authentication token if the server supports it."""
    result = client_from_ctx(ctx).post('/api/v1/auths/refresh')
    token = result.get('token') if isinstance(result, dict) else None
    if token:
        ctx.obj['state'].remember_auth(token, ctx.obj['state'].last_user)
        save_state(ctx)
    output(result, ctx.obj['as_json'])


@cli.group()
@click.pass_context
def chat(ctx: click.Context):
    """Chat completion commands."""


@chat.command('send')
@click.option('--model', '-m', required=True, help='Model ID')
@click.option('--prompt', '-p', default=None, help='Prompt text; reads stdin when omitted')
@click.option('--system', '-s', default=None, help='System prompt')
@click.option('--chat-id', default=None, help='Continue an existing chat')
@click.option('--file', 'files', multiple=True, help='RAG file ID for context')
@click.option('--collection', 'collections', multiple=True, help='RAG collection ID for context')
@click.option('--no-stream', is_flag=True, help='Wait for the complete response')
@click.option('--temperature', type=float, default=None)
@click.option('--max-tokens', type=int, default=None)
@click.pass_context
@command_guard
def chat_send(
    ctx: click.Context,
    model: str,
    prompt: str | None,
    system: str | None,
    chat_id: str | None,
    files: tuple[str, ...],
    collections: tuple[str, ...],
    no_stream: bool,
    temperature: float | None,
    max_tokens: int | None,
):
    """Send a chat message through OpenWebUI."""
    if prompt is None:
        if sys.stdin.isatty():
            raise RuntimeError('Prompt required. Use --prompt or pipe text on stdin.')
        prompt = sys.stdin.read().strip()
    result = chat_core.send_completion(
        client_from_ctx(ctx),
        model=model,
        prompt=prompt,
        system=system,
        chat_id=chat_id,
        files=list(files),
        collections=list(collections),
        stream=not no_stream,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    output(result, ctx.obj['as_json'])


@auth.group('api-key')
@click.pass_context
def auth_api_key(ctx: click.Context):
    """API key commands."""


@auth_api_key.command('create')
@click.pass_context
@command_guard
def api_key_create(ctx: click.Context):
    output(auth_core.api_key_create(client_from_ctx(ctx)), ctx.obj['as_json'])


@auth_api_key.command('get')
@click.pass_context
@command_guard
def api_key_get(ctx: click.Context):
    output(auth_core.api_key_get(client_from_ctx(ctx)), ctx.obj['as_json'])


@auth_api_key.command('delete')
@click.pass_context
@command_guard
def api_key_delete(ctx: click.Context):
    output(auth_core.api_key_delete(client_from_ctx(ctx)), ctx.obj['as_json'])


@cli.group()
@click.pass_context
def models(ctx: click.Context):
    """Model workspace commands."""


@models.command('list')
@click.option('--page', default=1, type=int)
@click.option('--query', default=None)
@click.pass_context
@command_guard
def models_list(ctx: click.Context, page: int, query: str | None):
    output(models_core.list_models(client_from_ctx(ctx), page=page, query=query), ctx.obj['as_json'])


@models.command('show')
@click.argument('model_id')
@click.pass_context
@command_guard
def models_show(ctx: click.Context, model_id: str):
    output(models_core.show_model(client_from_ctx(ctx), model_id), ctx.obj['as_json'])


@models.command('tags')
@click.pass_context
@command_guard
def models_tags(ctx: click.Context):
    output(models_core.tags(client_from_ctx(ctx)), ctx.obj['as_json'])


@models.command('base')
@click.pass_context
@command_guard
def models_base(ctx: click.Context):
    output(models_core.base(client_from_ctx(ctx)), ctx.obj['as_json'])


@models.command('export')
@click.pass_context
@command_guard
def models_export(ctx: click.Context):
    output(models_core.export(client_from_ctx(ctx)), ctx.obj['as_json'])


@models.command('sync')
@click.option('--data', default=None, help='JSON array of model objects')
@click.option('--data-file', default=None, type=click.Path(exists=True))
@click.pass_context
@command_guard
def models_sync(ctx: click.Context, data: str | None, data_file: str | None):
    payload = load_json_value(data, data_file)
    if not isinstance(payload, list):
        raise RuntimeError('models sync expects a JSON array')
    output(models_core.sync(client_from_ctx(ctx), payload), ctx.obj['as_json'])


@cli.group()
@click.pass_context
def rag(ctx: click.Context):
    """RAG and knowledge commands."""


@rag.group('collections')
@click.pass_context
def rag_collections(ctx: click.Context):
    """Knowledge collection commands."""


@rag_collections.command('list')
@click.pass_context
@command_guard
def rag_collections_list(ctx: click.Context):
    output(rag_core.list_collections(client_from_ctx(ctx)), ctx.obj['as_json'])


@rag_collections.command('create')
@click.argument('name')
@click.option('--description', '-d', default='')
@click.pass_context
@command_guard
def rag_collections_create(ctx: click.Context, name: str, description: str):
    output(rag_core.create_collection(client_from_ctx(ctx), name, description), ctx.obj['as_json'])


@rag_collections.command('delete')
@click.argument('collection_id')
@click.pass_context
@command_guard
def rag_collections_delete(ctx: click.Context, collection_id: str):
    output(rag_core.delete_collection(client_from_ctx(ctx), collection_id), ctx.obj['as_json'])


@rag_collections.command('add-file')
@click.argument('collection_id')
@click.argument('file_id')
@click.pass_context
@command_guard
def rag_collections_add_file(ctx: click.Context, collection_id: str, file_id: str):
    output(rag_core.add_file(client_from_ctx(ctx), collection_id, file_id), ctx.obj['as_json'])


@rag_collections.command('remove-file')
@click.argument('collection_id')
@click.argument('file_id')
@click.pass_context
@command_guard
def rag_collections_remove_file(ctx: click.Context, collection_id: str, file_id: str):
    output(rag_core.remove_file(client_from_ctx(ctx), collection_id, file_id), ctx.obj['as_json'])


@rag.command('search')
@click.option('--collection', required=True, help='Knowledge collection ID/name')
@click.option('--query', required=True, help='Search query')
@click.option('--top-k', default=5, type=int)
@click.pass_context
@command_guard
def rag_search(ctx: click.Context, collection: str, query: str, top_k: int):
    output(rag_core.search_collection(client_from_ctx(ctx), collection, query, top_k), ctx.obj['as_json'])


@cli.group()
@click.pass_context
def admin(ctx: click.Context):
    """Admin inspection commands."""


@admin.command('stats')
@click.pass_context
@command_guard
def admin_stats(ctx: click.Context):
    output(admin_core.stats(client_from_ctx(ctx)), ctx.obj['as_json'])


@admin.command('users')
@click.pass_context
@command_guard
def admin_users(ctx: click.Context):
    output(admin_core.users(client_from_ctx(ctx)), ctx.obj['as_json'])


@admin.command('config')
@click.pass_context
@command_guard
def admin_config(ctx: click.Context):
    output(admin_core.config(client_from_ctx(ctx)), ctx.obj['as_json'])


@cli.group()
@click.pass_context
def chats(ctx: click.Context):
    """Chat workspace commands."""


@chats.command('list')
@click.option('--page', default=None, type=int)
@click.pass_context
@command_guard
def chats_list(ctx: click.Context, page: int | None):
    output(chats_core.list_chats(client_from_ctx(ctx), page=page), ctx.obj['as_json'])


@chats.command('show')
@click.argument('chat_id')
@click.pass_context
@command_guard
def chats_show(ctx: click.Context, chat_id: str):
    output(chats_core.show_chat(client_from_ctx(ctx), chat_id), ctx.obj['as_json'])


@chats.command('create')
@click.option('--title', default='New Chat')
@click.option('--data', default=None, help='JSON chat body')
@click.option('--data-file', default=None, type=click.Path(exists=True))
@click.pass_context
@command_guard
def chats_create(ctx: click.Context, title: str, data: str | None, data_file: str | None):
    chat = load_json_value(data, data_file) if (data or data_file) else None
    result = chats_core.create_chat(client_from_ctx(ctx), title, chat)
    chat_id = result.get('id') if isinstance(result, dict) else None
    if chat_id:
        ctx.obj['state'].select_chat(chat_id)
        save_state(ctx)
    output(result, ctx.obj['as_json'])


@chats.command('update')
@click.argument('chat_id')
@click.option('--data', default=None, help='JSON chat body')
@click.option('--data-file', default=None, type=click.Path(exists=True))
@click.pass_context
@command_guard
def chats_update(ctx: click.Context, chat_id: str, data: str | None, data_file: str | None):
    payload = load_json_value(data, data_file)
    output(chats_core.update_chat(client_from_ctx(ctx), chat_id, payload), ctx.obj['as_json'])


@chats.command('delete')
@click.argument('chat_id')
@click.pass_context
@command_guard
def chats_delete(ctx: click.Context, chat_id: str):
    output(chats_core.delete_chat(client_from_ctx(ctx), chat_id), ctx.obj['as_json'])


@chats.command('pin')
@click.argument('chat_id')
@click.pass_context
@command_guard
def chats_pin(ctx: click.Context, chat_id: str):
    output(chats_core.pin_chat(client_from_ctx(ctx), chat_id), ctx.obj['as_json'])


@chats.command('archive')
@click.argument('chat_id')
@click.pass_context
@command_guard
def chats_archive(ctx: click.Context, chat_id: str):
    output(chats_core.archive_chat(client_from_ctx(ctx), chat_id), ctx.obj['as_json'])


@chats.command('clone')
@click.argument('chat_id')
@click.option('--title', default=None)
@click.pass_context
@command_guard
def chats_clone(ctx: click.Context, chat_id: str, title: str | None):
    output(chats_core.clone_chat(client_from_ctx(ctx), chat_id, title), ctx.obj['as_json'])


@chats.command('share')
@click.argument('chat_id')
@click.pass_context
@command_guard
def chats_share(ctx: click.Context, chat_id: str):
    output(chats_core.share_chat(client_from_ctx(ctx), chat_id), ctx.obj['as_json'])


@chats.command('select')
@click.argument('chat_id')
@click.pass_context
def chats_select(ctx: click.Context, chat_id: str):
    state: SessionState = ctx.obj['state']
    state.select_chat(chat_id)
    save_state(ctx)
    output({'current_chat_id': state.current_chat_id}, ctx.obj['as_json'])


@chats.group('tag')
@click.pass_context
def chats_tag(ctx: click.Context):
    """Chat tag commands."""


@chats_tag.command('add')
@click.argument('chat_id')
@click.argument('name')
@click.pass_context
@command_guard
def chats_tag_add(ctx: click.Context, chat_id: str, name: str):
    output(chats_core.add_tag(client_from_ctx(ctx), chat_id, name), ctx.obj['as_json'])


@chats_tag.command('remove')
@click.argument('chat_id')
@click.argument('name')
@click.pass_context
@command_guard
def chats_tag_remove(ctx: click.Context, chat_id: str, name: str):
    output(chats_core.remove_tag(client_from_ctx(ctx), chat_id, name), ctx.obj['as_json'])


@cli.group()
@click.pass_context
def files(ctx: click.Context):
    """File workspace commands."""


@files.command('list')
@click.pass_context
@command_guard
def files_list(ctx: click.Context):
    output(files_core.list_files(client_from_ctx(ctx)), ctx.obj['as_json'])


@files.command('show')
@click.argument('file_id')
@click.pass_context
@command_guard
def files_show(ctx: click.Context, file_id: str):
    output(files_core.show_file(client_from_ctx(ctx), file_id), ctx.obj['as_json'])


@files.command('upload')
@click.argument('path', type=click.Path(exists=True))
@click.pass_context
@command_guard
def files_upload(ctx: click.Context, path: str):
    output(files_core.upload_file(client_from_ctx(ctx), path), ctx.obj['as_json'])


@files.command('delete')
@click.argument('file_id')
@click.pass_context
@command_guard
def files_delete(ctx: click.Context, file_id: str):
    output(files_core.delete_file(client_from_ctx(ctx), file_id), ctx.obj['as_json'])


@files.command('content')
@click.argument('file_id')
@click.pass_context
@command_guard
def files_content(ctx: click.Context, file_id: str):
    output(files_core.content(client_from_ctx(ctx), file_id), ctx.obj['as_json'])


@cli.group()
@click.pass_context
def users(ctx: click.Context):
    """User inspection commands."""


@users.command('list')
@click.pass_context
@command_guard
def users_list(ctx: click.Context):
    output(users_core.list_users(client_from_ctx(ctx)), ctx.obj['as_json'])


@users.command('all')
@click.pass_context
@command_guard
def users_all(ctx: click.Context):
    output(users_core.all_users(client_from_ctx(ctx)), ctx.obj['as_json'])


@users.command('search')
@click.argument('query')
@click.pass_context
@command_guard
def users_search(ctx: click.Context, query: str):
    output(users_core.search_users(client_from_ctx(ctx), query), ctx.obj['as_json'])


@users.command('me')
@click.pass_context
@command_guard
def users_me(ctx: click.Context):
    output(users_core.current_user_info(client_from_ctx(ctx)), ctx.obj['as_json'])


@cli.group()
@click.pass_context
def memories(ctx: click.Context):
    """User memory commands."""


@memories.command('list')
@click.pass_context
@command_guard
def memories_list(ctx: click.Context):
    output(memories_core.list_memories(client_from_ctx(ctx)), ctx.obj['as_json'])


@memories.command('add')
@click.option('--content', required=True)
@click.pass_context
@command_guard
def memories_add(ctx: click.Context, content: str):
    output(memories_core.add_memory(client_from_ctx(ctx), content), ctx.obj['as_json'])


@memories.command('query')
@click.option('--content', required=True)
@click.option('--top-k', default=1, type=int)
@click.pass_context
@command_guard
def memories_query(ctx: click.Context, content: str, top_k: int):
    output(memories_core.query_memories(client_from_ctx(ctx), content, top_k), ctx.obj['as_json'])


@memories.command('update')
@click.argument('memory_id')
@click.option('--content', required=True)
@click.pass_context
@command_guard
def memories_update(ctx: click.Context, memory_id: str, content: str):
    output(memories_core.update_memory(client_from_ctx(ctx), memory_id, content), ctx.obj['as_json'])


@memories.command('delete')
@click.argument('memory_id')
@click.pass_context
@command_guard
def memories_delete(ctx: click.Context, memory_id: str):
    output(memories_core.delete_memory(client_from_ctx(ctx), memory_id), ctx.obj['as_json'])


@memories.command('reset')
@click.pass_context
@command_guard
def memories_reset(ctx: click.Context):
    output(memories_core.reset_memories(client_from_ctx(ctx)), ctx.obj['as_json'])


@memories.command('clear')
@click.pass_context
@command_guard
def memories_clear(ctx: click.Context):
    output(memories_core.clear_memories(client_from_ctx(ctx)), ctx.obj['as_json'])


@cli.group()
@click.pass_context
def notes(ctx: click.Context):
    """Notebook commands."""


@notes.command('list')
@click.option('--page', default=None, type=int)
@click.option('--pinned', is_flag=True, help='List pinned notes')
@click.pass_context
@command_guard
def notes_list(ctx: click.Context, page: int | None, pinned: bool):
    if pinned:
        result = notes_core.list_pinned_notes(client_from_ctx(ctx))
    else:
        result = notes_core.list_notes(client_from_ctx(ctx), page=page)
    output(result, ctx.obj['as_json'])


@notes.command('search')
@click.option('--query', default=None)
@click.option('--view-option', default=None)
@click.option('--permission', default=None)
@click.option('--order-by', default=None)
@click.option('--direction', default=None)
@click.option('--page', default=1, type=int)
@click.pass_context
@command_guard
def notes_search(
    ctx: click.Context,
    query: str | None,
    view_option: str | None,
    permission: str | None,
    order_by: str | None,
    direction: str | None,
    page: int,
):
    output(
        notes_core.search_notes(
            client_from_ctx(ctx),
            query=query,
            view_option=view_option,
            permission=permission,
            order_by=order_by,
            direction=direction,
            page=page,
        ),
        ctx.obj['as_json'],
    )


@notes.command('show')
@click.argument('note_id')
@click.pass_context
@command_guard
def notes_show(ctx: click.Context, note_id: str):
    output(notes_core.show_note(client_from_ctx(ctx), note_id), ctx.obj['as_json'])


@notes.command('create')
@click.option('--title', required=True)
@click.option('--data', default=None)
@click.option('--data-file', default=None, type=click.Path(exists=True))
@click.option('--meta', default=None)
@click.option('--meta-file', default=None, type=click.Path(exists=True))
@click.option('--access-grants', default=None)
@click.option('--access-grants-file', default=None, type=click.Path(exists=True))
@click.pass_context
@command_guard
def notes_create(
    ctx: click.Context,
    title: str,
    data: str | None,
    data_file: str | None,
    meta: str | None,
    meta_file: str | None,
    access_grants: str | None,
    access_grants_file: str | None,
):
    grants = require_list(load_optional_json_value(access_grants, access_grants_file, []), 'access grants')
    output(
        notes_core.create_note(
            client_from_ctx(ctx),
            title,
            data=load_optional_json_value(data, data_file, {}),
            meta=load_optional_json_value(meta, meta_file, {}),
            access_grants=grants,
        ),
        ctx.obj['as_json'],
    )


@notes.command('update')
@click.argument('note_id')
@click.option('--title', required=True)
@click.option('--data', default=None)
@click.option('--data-file', default=None, type=click.Path(exists=True))
@click.option('--meta', default=None)
@click.option('--meta-file', default=None, type=click.Path(exists=True))
@click.option('--access-grants', default=None)
@click.option('--access-grants-file', default=None, type=click.Path(exists=True))
@click.pass_context
@command_guard
def notes_update(
    ctx: click.Context,
    note_id: str,
    title: str,
    data: str | None,
    data_file: str | None,
    meta: str | None,
    meta_file: str | None,
    access_grants: str | None,
    access_grants_file: str | None,
):
    grants = require_list(load_optional_json_value(access_grants, access_grants_file, []), 'access grants')
    output(
        notes_core.update_note(
            client_from_ctx(ctx),
            note_id,
            title,
            data=load_optional_json_value(data, data_file, {}),
            meta=load_optional_json_value(meta, meta_file, {}),
            access_grants=grants,
        ),
        ctx.obj['as_json'],
    )


@notes.group('access')
@click.pass_context
def notes_access(ctx: click.Context):
    """Note access commands."""


@notes_access.command('set')
@click.argument('note_id')
@click.option('--access-grants', default=None)
@click.option('--access-grants-file', default=None, type=click.Path(exists=True))
@click.pass_context
@command_guard
def notes_access_set(ctx: click.Context, note_id: str, access_grants: str | None, access_grants_file: str | None):
    grants = require_list(load_optional_json_value(access_grants, access_grants_file, []), 'access grants')
    output(notes_core.update_note_access(client_from_ctx(ctx), note_id, grants), ctx.obj['as_json'])


@notes.command('pin')
@click.argument('note_id')
@click.pass_context
@command_guard
def notes_pin(ctx: click.Context, note_id: str):
    output(notes_core.pin_note(client_from_ctx(ctx), note_id), ctx.obj['as_json'])


@notes.command('delete')
@click.argument('note_id')
@click.pass_context
@command_guard
def notes_delete(ctx: click.Context, note_id: str):
    output(notes_core.delete_note(client_from_ctx(ctx), note_id), ctx.obj['as_json'])


def build_prompt_payload(
    command: str,
    name: str,
    content: str | None,
    content_file: str | None,
    data: str | None,
    data_file: str | None,
    meta: str | None,
    meta_file: str | None,
    tags: tuple[str, ...],
    access_grants: str | None,
    access_grants_file: str | None,
    commit_message: str | None,
    non_production: bool,
) -> dict[str, Any]:
    content_value = load_text_value(content, content_file)
    if content_value is None:
        raise RuntimeError('Prompt content required. Use --content or --content-file.')
    grants = require_list(load_optional_json_value(access_grants, access_grants_file, []), 'access grants')
    payload = {
        'command': command,
        'name': name,
        'content': content_value,
        'data': load_optional_json_value(data, data_file, {}),
        'meta': load_optional_json_value(meta, meta_file, {}),
        'tags': list(tags),
        'access_grants': grants,
        'is_production': not non_production,
    }
    if commit_message:
        payload['commit_message'] = commit_message
    return payload


@cli.group()
@click.pass_context
def prompts(ctx: click.Context):
    """Prompt library commands."""


@prompts.command('list')
@click.option('--page', default=1, type=int)
@click.option('--query', default=None)
@click.option('--view-option', default=None)
@click.option('--tag', default=None)
@click.option('--order-by', default=None)
@click.option('--direction', default=None)
@click.pass_context
@command_guard
def prompts_list(
    ctx: click.Context,
    page: int,
    query: str | None,
    view_option: str | None,
    tag: str | None,
    order_by: str | None,
    direction: str | None,
):
    output(
        prompts_core.list_prompts(
            client_from_ctx(ctx),
            page=page,
            query=query,
            view_option=view_option,
            tag=tag,
            order_by=order_by,
            direction=direction,
        ),
        ctx.obj['as_json'],
    )


@prompts.command('tags')
@click.pass_context
@command_guard
def prompts_tags(ctx: click.Context):
    output(prompts_core.tags(client_from_ctx(ctx)), ctx.obj['as_json'])


@prompts.command('show')
@click.argument('prompt_id')
@click.pass_context
@command_guard
def prompts_show(ctx: click.Context, prompt_id: str):
    output(prompts_core.show_prompt(client_from_ctx(ctx), prompt_id), ctx.obj['as_json'])


@prompts.command('create')
@click.option('--command', 'prompt_command', required=True)
@click.option('--name', required=True)
@click.option('--content', default=None)
@click.option('--content-file', default=None, type=click.Path(exists=True))
@click.option('--data', default=None)
@click.option('--data-file', default=None, type=click.Path(exists=True))
@click.option('--meta', default=None)
@click.option('--meta-file', default=None, type=click.Path(exists=True))
@click.option('--tag', 'tags', multiple=True)
@click.option('--access-grants', default=None)
@click.option('--access-grants-file', default=None, type=click.Path(exists=True))
@click.option('--commit-message', default=None)
@click.option('--non-production', is_flag=True)
@click.pass_context
@command_guard
def prompts_create(
    ctx: click.Context,
    prompt_command: str,
    name: str,
    content: str | None,
    content_file: str | None,
    data: str | None,
    data_file: str | None,
    meta: str | None,
    meta_file: str | None,
    tags: tuple[str, ...],
    access_grants: str | None,
    access_grants_file: str | None,
    commit_message: str | None,
    non_production: bool,
):
    output(
        prompts_core.create_prompt(
            client_from_ctx(ctx),
            build_prompt_payload(
                prompt_command,
                name,
                content,
                content_file,
                data,
                data_file,
                meta,
                meta_file,
                tags,
                access_grants,
                access_grants_file,
                commit_message,
                non_production,
            ),
        ),
        ctx.obj['as_json'],
    )


@prompts.command('update')
@click.argument('prompt_id')
@click.option('--command', 'prompt_command', required=True)
@click.option('--name', required=True)
@click.option('--content', default=None)
@click.option('--content-file', default=None, type=click.Path(exists=True))
@click.option('--data', default=None)
@click.option('--data-file', default=None, type=click.Path(exists=True))
@click.option('--meta', default=None)
@click.option('--meta-file', default=None, type=click.Path(exists=True))
@click.option('--tag', 'tags', multiple=True)
@click.option('--access-grants', default=None)
@click.option('--access-grants-file', default=None, type=click.Path(exists=True))
@click.option('--commit-message', default=None)
@click.option('--non-production', is_flag=True)
@click.pass_context
@command_guard
def prompts_update(
    ctx: click.Context,
    prompt_id: str,
    prompt_command: str,
    name: str,
    content: str | None,
    content_file: str | None,
    data: str | None,
    data_file: str | None,
    meta: str | None,
    meta_file: str | None,
    tags: tuple[str, ...],
    access_grants: str | None,
    access_grants_file: str | None,
    commit_message: str | None,
    non_production: bool,
):
    output(
        prompts_core.update_prompt(
            client_from_ctx(ctx),
            prompt_id,
            build_prompt_payload(
                prompt_command,
                name,
                content,
                content_file,
                data,
                data_file,
                meta,
                meta_file,
                tags,
                access_grants,
                access_grants_file,
                commit_message,
                non_production,
            ),
        ),
        ctx.obj['as_json'],
    )


@prompts.command('update-meta')
@click.argument('prompt_id')
@click.option('--command', 'prompt_command', required=True)
@click.option('--name', required=True)
@click.option('--tag', 'tags', multiple=True)
@click.pass_context
@command_guard
def prompts_update_meta(ctx: click.Context, prompt_id: str, prompt_command: str, name: str, tags: tuple[str, ...]):
    output(
        prompts_core.update_prompt_metadata(client_from_ctx(ctx), prompt_id, name=name, command=prompt_command, tags=list(tags)),
        ctx.obj['as_json'],
    )


@prompts.command('version')
@click.argument('prompt_id')
@click.option('--version-id', required=True)
@click.pass_context
@command_guard
def prompts_version(ctx: click.Context, prompt_id: str, version_id: str):
    output(prompts_core.set_prompt_version(client_from_ctx(ctx), prompt_id, version_id), ctx.obj['as_json'])


@prompts.command('toggle')
@click.argument('prompt_id')
@click.pass_context
@command_guard
def prompts_toggle(ctx: click.Context, prompt_id: str):
    output(prompts_core.toggle_prompt(client_from_ctx(ctx), prompt_id), ctx.obj['as_json'])


@prompts.command('delete')
@click.argument('prompt_id')
@click.pass_context
@command_guard
def prompts_delete(ctx: click.Context, prompt_id: str):
    output(prompts_core.delete_prompt(client_from_ctx(ctx), prompt_id), ctx.obj['as_json'])


@prompts.group('history')
@click.pass_context
def prompts_history(ctx: click.Context):
    """Prompt history commands."""


@prompts_history.command('list')
@click.argument('prompt_id')
@click.option('--page', default=0, type=int)
@click.pass_context
@command_guard
def prompts_history_list(ctx: click.Context, prompt_id: str, page: int):
    output(prompts_core.list_prompt_history(client_from_ctx(ctx), prompt_id, page=page), ctx.obj['as_json'])


@prompts_history.command('show')
@click.argument('prompt_id')
@click.argument('history_id')
@click.pass_context
@command_guard
def prompts_history_show(ctx: click.Context, prompt_id: str, history_id: str):
    output(prompts_core.show_prompt_history(client_from_ctx(ctx), prompt_id, history_id), ctx.obj['as_json'])


@prompts_history.command('diff')
@click.argument('prompt_id')
@click.option('--from-id', 'from_id', required=True)
@click.option('--to-id', 'to_id', required=True)
@click.pass_context
@command_guard
def prompts_history_diff(ctx: click.Context, prompt_id: str, from_id: str, to_id: str):
    output(prompts_core.diff_prompt_history(client_from_ctx(ctx), prompt_id, from_id, to_id), ctx.obj['as_json'])


@prompts_history.command('delete')
@click.argument('prompt_id')
@click.argument('history_id')
@click.pass_context
@command_guard
def prompts_history_delete(ctx: click.Context, prompt_id: str, history_id: str):
    output(prompts_core.delete_prompt_history(client_from_ctx(ctx), prompt_id, history_id), ctx.obj['as_json'])


@cli.group()
@click.pass_context
def automations(ctx: click.Context):
    """Automation commands."""


@automations.command('list')
@click.option('--query', default=None)
@click.option('--status', default=None, type=click.Choice(['active', 'paused']))
@click.option('--page', default=1, type=int)
@click.pass_context
@command_guard
def automations_list(ctx: click.Context, query: str | None, status: str | None, page: int):
    output(automations_core.list_automations(client_from_ctx(ctx), query=query, status=status, page=page), ctx.obj['as_json'])


@automations.command('show')
@click.argument('automation_id')
@click.pass_context
@command_guard
def automations_show(ctx: click.Context, automation_id: str):
    output(automations_core.show_automation(client_from_ctx(ctx), automation_id), ctx.obj['as_json'])


@automations.command('create')
@click.option('--name', default=None)
@click.option('--prompt', default=None)
@click.option('--model', 'model_id', default=None)
@click.option('--rrule', default=None)
@click.option('--terminal-server-id', default=None)
@click.option('--terminal-cwd', default=None)
@click.option('--meta', default=None)
@click.option('--meta-file', default=None, type=click.Path(exists=True))
@click.option('--inactive', is_flag=True)
@click.option('--data', default=None)
@click.option('--data-file', default=None, type=click.Path(exists=True))
@click.pass_context
@command_guard
def automations_create(
    ctx: click.Context,
    name: str | None,
    prompt: str | None,
    model_id: str | None,
    rrule: str | None,
    terminal_server_id: str | None,
    terminal_cwd: str | None,
    meta: str | None,
    meta_file: str | None,
    inactive: bool,
    data: str | None,
    data_file: str | None,
):
    if data or data_file:
        payload = load_json_value(data, data_file)
    else:
        missing = [label for label, value in {'--name': name, '--prompt': prompt, '--model': model_id, '--rrule': rrule}.items() if not value]
        if missing:
            raise RuntimeError(f'automations create requires {", ".join(missing)} unless --data or --data-file is used')
        automation_data: dict[str, Any] = {'prompt': prompt, 'model_id': model_id, 'rrule': rrule}
        if terminal_server_id:
            automation_data['terminal'] = {'server_id': terminal_server_id}
            if terminal_cwd:
                automation_data['terminal']['cwd'] = terminal_cwd
        payload = {
            'name': name,
            'data': automation_data,
            'meta': load_optional_json_value(meta, meta_file, {}),
            'is_active': not inactive,
        }
    output(automations_core.create_automation(client_from_ctx(ctx), payload), ctx.obj['as_json'])


@automations.command('update')
@click.argument('automation_id')
@click.option('--data', default=None)
@click.option('--data-file', default=None, type=click.Path(exists=True))
@click.pass_context
@command_guard
def automations_update(ctx: click.Context, automation_id: str, data: str | None, data_file: str | None):
    if not (data or data_file):
        raise RuntimeError('automations update requires --data or --data-file with a full AutomationForm payload')
    output(automations_core.update_automation(client_from_ctx(ctx), automation_id, load_json_value(data, data_file)), ctx.obj['as_json'])


@automations.command('toggle')
@click.argument('automation_id')
@click.pass_context
@command_guard
def automations_toggle(ctx: click.Context, automation_id: str):
    output(automations_core.toggle_automation(client_from_ctx(ctx), automation_id), ctx.obj['as_json'])


@automations.command('run')
@click.argument('automation_id')
@click.pass_context
@command_guard
def automations_run(ctx: click.Context, automation_id: str):
    output(automations_core.run_automation(client_from_ctx(ctx), automation_id), ctx.obj['as_json'])


@automations.command('delete')
@click.argument('automation_id')
@click.pass_context
@command_guard
def automations_delete(ctx: click.Context, automation_id: str):
    output(automations_core.delete_automation(client_from_ctx(ctx), automation_id), ctx.obj['as_json'])


@automations.command('runs')
@click.argument('automation_id')
@click.option('--skip', default=0, type=int)
@click.option('--limit', default=50, type=int)
@click.pass_context
@command_guard
def automations_runs(ctx: click.Context, automation_id: str, skip: int, limit: int):
    output(automations_core.list_automation_runs(client_from_ctx(ctx), automation_id, skip=skip, limit=limit), ctx.obj['as_json'])


@cli.group()
@click.pass_context
def api(ctx: click.Context):
    """Generic API endpoint access."""


@api.command('get')
@click.argument('endpoint')
@click.pass_context
@command_guard
def api_get(ctx: click.Context, endpoint: str):
    output(client_from_ctx(ctx).get(endpoint), ctx.obj['as_json'])


@api.command('post')
@click.argument('endpoint')
@click.option('--data', default=None, help='JSON request body')
@click.option('--data-file', default=None, type=click.Path(exists=True))
@click.pass_context
@command_guard
def api_post(ctx: click.Context, endpoint: str, data: str | None, data_file: str | None):
    output(client_from_ctx(ctx).post(endpoint, load_json_value(data, data_file)), ctx.obj['as_json'])


@api.command('delete')
@click.argument('endpoint')
@click.option('--data', default=None, help='Optional JSON request body')
@click.option('--data-file', default=None, type=click.Path(exists=True))
@click.pass_context
@command_guard
def api_delete(ctx: click.Context, endpoint: str, data: str | None, data_file: str | None):
    payload = load_json_value(data, data_file) if (data or data_file) else None
    output(client_from_ctx(ctx).delete(endpoint, payload), ctx.obj['as_json'])


@cli.group()
@click.pass_context
def session(ctx: click.Context):
    """Local harness session state."""


@session.command('status')
@click.pass_context
def session_status(ctx: click.Context):
    output(ctx.obj['state'].masked(), ctx.obj['as_json'])


@session.command('select')
@click.argument('chat_id')
@click.pass_context
def session_select(ctx: click.Context, chat_id: str):
    state: SessionState = ctx.obj['state']
    state.select_chat(chat_id)
    save_state(ctx)
    output({'current_chat_id': state.current_chat_id}, ctx.obj['as_json'])


@session.command('undo')
@click.pass_context
def session_undo(ctx: click.Context):
    state: SessionState = ctx.obj['state']
    changed = state.undo()
    if changed:
        save_state(ctx)
    output({'changed': changed, 'state': state.masked()}, ctx.obj['as_json'])


@session.command('redo')
@click.pass_context
def session_redo(ctx: click.Context):
    state: SessionState = ctx.obj['state']
    changed = state.redo()
    if changed:
        save_state(ctx)
    output({'changed': changed, 'state': state.masked()}, ctx.obj['as_json'])


if __name__ == '__main__':
    main()
