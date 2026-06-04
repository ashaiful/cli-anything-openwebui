import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


def _resolve_cli(name):
    """Resolve installed CLI command; falls back to python -m for dev."""
    force = os.environ.get('CLI_ANYTHING_FORCE_INSTALLED', '').strip() == '1'
    path = shutil.which(name)
    if path:
        print(f'[_resolve_cli] Using installed command: {path}')
        return [path]
    if force:
        raise RuntimeError(f'{name} not found in PATH. Install with: pip install -e .')
    module = name.replace('cli-anything-', 'cli_anything.') + '.' + name.split('-')[-1] + '_cli'
    if name == 'cli-anything-openwebui':
        module = 'cli_anything.openwebui.openwebui_cli'
    print(f'[_resolve_cli] Falling back to: {sys.executable} -m {module}')
    return [sys.executable, '-m', module]


class OpenWebUIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        if path == '/api/v1/models/tags':
            self._json(['default', 'reasoning'])
        elif path == '/api/v1/private':
            self._json({'detail': 'unauthorized'}, status=401)
        elif path == '/api/v1/broken':
            self._json({'detail': 'server error'}, status=500)
        elif path == '/api/v1/knowledge/':
            self._json([{'id': 'kb-1', 'name': 'Runtime Docs', 'description': 'Docs'}])
        elif path == '/api/v1/users/':
            self._json([{'id': 'user-1', 'email': 'agent@example.com', 'role': 'admin'}])
        elif path == '/api/v1/auths/admin/config':
            self._json({'ENABLE_SIGNUP': True})
        elif path == '/api/v1/auths/':
            auth = self.headers.get('Authorization')
            self._json({'id': 'user-1', 'email': 'agent@example.com', 'role': 'admin', 'auth': auth})
        elif path == '/api/v1/memories/':
            self._json(
                [
                    {
                        'id': 'mem-1',
                        'user_id': 'user-1',
                        'content': 'Prefers concise answers',
                        'created_at': 1710000000,
                        'updated_at': 1710000000,
                    }
                ]
            )
        elif path == '/api/v1/notes/':
            self._json(
                [
                    {
                        'id': 'note-1',
                        'title': 'Runbook',
                        'data': {'content': {'md': 'hello'}},
                        'is_pinned': False,
                        'query': query,
                    }
                ]
            )
        elif path == '/api/v1/notes/pinned':
            self._json([{'id': 'note-1', 'title': 'Runbook', 'is_pinned': True}])
        elif path == '/api/v1/notes/search':
            self._json({'items': [{'id': 'note-1', 'title': 'Runbook', 'query': query}], 'total': 1})
        elif path == '/api/v1/notes/note-1':
            self._json({'id': 'note-1', 'title': 'Runbook', 'data': {'content': {'md': 'full'}}, 'write_access': True})
        elif path == '/api/v1/prompts/tags':
            self._json(['writing', 'support'])
        elif path == '/api/v1/prompts/list':
            self._json(
                {
                    'items': [
                        {
                            'id': 'prompt-1',
                            'command': '/summarize',
                            'name': 'Summarize',
                            'content': 'Summarize {{text}}',
                            'tags': ['writing'],
                            'is_active': True,
                            'write_access': True,
                            'query': query,
                        }
                    ],
                    'total': 1,
                }
            )
        elif path == '/api/v1/prompts/id/prompt-1':
            self._json({'id': 'prompt-1', 'command': '/summarize', 'name': 'Summarize', 'write_access': True})
        elif path == '/api/v1/prompts/id/prompt-1/history':
            self._json([{'id': 'hist-1', 'prompt_id': 'prompt-1', 'snapshot': {'content': 'old'}, 'query': query}])
        elif path == '/api/v1/prompts/id/prompt-1/history/hist-1':
            self._json({'id': 'hist-1', 'prompt_id': 'prompt-1', 'snapshot': {'content': 'old'}})
        elif path == '/api/v1/prompts/id/prompt-1/history/diff':
            self._json(
                {
                    'from_id': query.get('from_id'),
                    'to_id': query.get('to_id'),
                    'from_snapshot': {'content': 'old'},
                    'to_snapshot': {'content': 'new'},
                    'content_diff': ['-old', '+new'],
                    'name_changed': False,
                }
            )
        elif path == '/api/v1/automations/list':
            self._json({'items': [{'id': 'auto-1', 'name': 'Daily summary', 'query': query}], 'total': 1})
        elif path == '/api/v1/automations/auto-1/runs':
            self._json([{'id': 'run-1', 'automation_id': 'auto-1', 'status': 'completed', 'query': query}])
        elif path == '/api/v1/automations/auto-1':
            self._json({'id': 'auto-1', 'name': 'Daily summary', 'is_active': True})
        else:
            self._json({'path': self.path})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get('Content-Length', '0'))
        payload = json.loads(self.rfile.read(length) or b'{}')
        if path == '/api/v1/auths/signin':
            self._json(
                {
                    'token': 'token-123',
                    'token_type': 'Bearer',
                    'id': 'user-1',
                    'email': payload.get('email'),
                    'name': 'Agent User',
                    'role': 'admin',
                }
            )
        elif path == '/api/chat/completions':
            self._json(
                {
                    'choices': [{'message': {'content': f"echo: {payload['messages'][-1]['content']}"}}],
                    'payload': payload,
                }
            )
        elif path == '/api/v1/knowledge/create':
            self._json({'id': 'kb-new', 'name': payload.get('name'), 'description': payload.get('description')})
        elif path == '/api/v1/retrieval/query/collection':
            self._json({'results': [{'content': 'deployment steps', 'score': 0.1}], 'payload': payload})
        elif path == '/api/v1/memories/add':
            self._json({'id': 'mem-new', 'user_id': 'user-1', 'content': payload.get('content'), 'payload': payload})
        elif path == '/api/v1/memories/query':
            self._json(
                {
                    'ids': [['mem-1']],
                    'documents': [['Prefers concise answers']],
                    'metadatas': [[{'created_at': 1710000000}]],
                    'distances': [[0.91]],
                    'payload': payload,
                }
            )
        elif path == '/api/v1/memories/mem-1/update':
            self._json({'id': 'mem-1', 'user_id': 'user-1', 'content': payload.get('content'), 'payload': payload})
        elif path == '/api/v1/memories/reset':
            self._json(True)
        elif path == '/api/v1/notes/create':
            self._json({'id': 'note-new', 'payload': payload, **payload})
        elif path == '/api/v1/notes/note-1/update':
            self._json({'id': 'note-1', 'payload': payload, **payload})
        elif path == '/api/v1/notes/note-1/access/update':
            self._json({'id': 'note-1', 'payload': payload})
        elif path == '/api/v1/notes/note-1/pin':
            self._json({'id': 'note-1', 'is_pinned': True})
        elif path == '/api/v1/prompts/create':
            self._json({'id': 'prompt-new', 'user_id': 'user-1', 'version_id': 'hist-new', 'payload': payload, **payload})
        elif path == '/api/v1/prompts/id/prompt-1/update':
            self._json({'id': 'prompt-1', 'payload': payload, **payload})
        elif path == '/api/v1/prompts/id/prompt-1/update/meta':
            self._json({'id': 'prompt-1', 'payload': payload, **payload})
        elif path == '/api/v1/prompts/id/prompt-1/update/version':
            self._json({'id': 'prompt-1', 'payload': payload, 'version_id': payload.get('version_id')})
        elif path == '/api/v1/prompts/id/prompt-1/toggle':
            self._json({'id': 'prompt-1', 'is_active': False})
        elif path == '/api/v1/automations/create':
            self._json({'id': 'auto-new', 'payload': payload, **payload})
        elif path == '/api/v1/automations/auto-1/update':
            self._json({'id': 'auto-1', 'payload': payload, **payload})
        elif path == '/api/v1/automations/auto-1/toggle':
            self._json({'id': 'auto-1', 'is_active': False})
        elif path == '/api/v1/automations/auto-1/run':
            self._json({'id': 'auto-1', 'status': 'queued'})
        else:
            self._json({'path': self.path, 'payload': payload})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in (
            '/api/v1/memories/mem-1',
            '/api/v1/memories/delete/user',
            '/api/v1/notes/note-1/delete',
            '/api/v1/prompts/id/prompt-1/delete',
            '/api/v1/prompts/id/prompt-1/history/hist-2',
            '/api/v1/automations/auto-1/delete',
        ):
            self._json(True)
        else:
            self._json({'path': self.path})

    def log_message(self, format, *args):
        return

    def _json(self, payload, status=200):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _serve_openwebui_like_api():
    server = HTTPServer(('127.0.0.1', 0), OpenWebUIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f'http://127.0.0.1:{server.server_port}'


class TestCLISubprocess:
    CLI_BASE = _resolve_cli('cli-anything-openwebui')

    def _run(self, args, check=True):
        return subprocess.run(self.CLI_BASE + args, capture_output=True, text=True, check=check)

    def test_config_show_json_uses_openwebui_environment(self, monkeypatch):
        monkeypatch.setenv('OPENWEBUI_BASE_URL', 'http://env-openwebui.test')
        monkeypatch.setenv('OPENWEBUI_TOKEN', 'env-token')

        result = self._run(['--json', 'config', 'show'])
        data = json.loads(result.stdout)

        assert data['base_url'] == 'http://env-openwebui.test'
        assert data['token'] == '***'

    def test_help(self):
        result = self._run(['--help'])

        assert result.returncode == 0
        assert 'OpenWebUI' in result.stdout

    def test_config_show_json_masks_token(self, tmp_path):
        config = tmp_path / 'session.json'
        config.write_text(
            json.dumps(
                {
                    'base_url': 'http://example.test',
                    'token': 'secret-token',
                    'current_chat_id': None,
                    'undo_stack': [],
                    'redo_stack': [],
                    'last_user': {'email': 'agent@example.com'},
                }
            )
        )

        result = self._run(['--json', '--config', str(config), 'config', 'show'])
        data = json.loads(result.stdout)

        assert data['base_url'] == 'http://example.test'
        assert data['token'] == '***'
        assert data['last_user']['email'] == 'agent@example.com'

    def test_config_show_yaml_output(self, tmp_path):
        config = tmp_path / 'session.json'
        config.write_text(json.dumps({'base_url': 'http://yaml.test', 'token': 'secret-token'}))

        result = self._run(['--format', 'yaml', '--config', str(config), 'config', 'show'])

        assert 'base_url: http://yaml.test' in result.stdout
        assert 'token: ' in result.stdout
        assert 'secret-token' not in result.stdout

    def test_profile_set_and_use(self, tmp_path):
        config = tmp_path / 'session.json'

        self._run(
            [
                '--config',
                str(config),
                'profile',
                'set',
                'prod',
                '--base-url',
                'https://prod.example.com',
                '--token',
                'prod-token',
                '--default',
            ]
        )
        result = self._run(['--json', '--config', str(config), '--profile', 'prod', 'config', 'show'])
        data = json.loads(result.stdout)

        assert data['base_url'] == 'https://prod.example.com'
        assert data['token'] == '***'
        assert data['default_profile'] == 'prod'

    def test_api_get_returns_json_from_openwebui_like_server(self):
        server, base_url = _serve_openwebui_like_api()
        try:
            result = self._run(['--json', '--base-url', base_url, 'api', 'get', '/api/v1/models/tags'])
            data = json.loads(result.stdout)
        finally:
            server.shutdown()

        assert data == ['default', 'reasoning']

    def test_signin_persists_token_and_user(self, tmp_path):
        server, base_url = _serve_openwebui_like_api()
        config = tmp_path / 'session.json'
        try:
            result = self._run(
                [
                    '--json',
                    '--base-url',
                    base_url,
                    '--config',
                    str(config),
                    'auth',
                    'signin',
                    '--email',
                    'agent@example.com',
                    '--password',
                    'pw',
                ]
            )
            data = json.loads(result.stdout)
        finally:
            server.shutdown()

        saved = json.loads(config.read_text())
        assert data['email'] == 'agent@example.com'
        assert saved['token'] == 'token-123'
        assert saved['last_user']['id'] == 'user-1'

    def test_chat_send_posts_completion_payload(self):
        server, base_url = _serve_openwebui_like_api()
        try:
            result = self._run(
                [
                    '--json',
                    '--base-url',
                    base_url,
                    'chat',
                    'send',
                    '--model',
                    'assistant-model',
                    '--prompt',
                    'Hello runtime',
                    '--system',
                    'Be brief',
                    '--no-stream',
                    '--temperature',
                    '0.2',
                    '--max-tokens',
                    '64',
                ]
            )
            data = json.loads(result.stdout)
        finally:
            server.shutdown()

        assert data['content'] == 'echo: Hello runtime'
        assert data['response']['payload']['model'] == 'assistant-model'
        assert data['response']['payload']['messages'][0]['role'] == 'system'
        assert data['response']['payload']['temperature'] == 0.2
        assert data['response']['payload']['max_tokens'] == 64

    def test_rag_collections_and_search(self):
        server, base_url = _serve_openwebui_like_api()
        try:
            list_result = self._run(['--json', '--base-url', base_url, 'rag', 'collections', 'list'])
            create_result = self._run(
                [
                    '--json',
                    '--base-url',
                    base_url,
                    'rag',
                    'collections',
                    'create',
                    'New Docs',
                    '--description',
                    'Imported docs',
                ]
            )
            search_result = self._run(
                [
                    '--json',
                    '--base-url',
                    base_url,
                    'rag',
                    'search',
                    '--collection',
                    'kb-1',
                    '--query',
                    'deployment',
                    '--top-k',
                    '3',
                ]
            )
        finally:
            server.shutdown()

        assert json.loads(list_result.stdout)[0]['id'] == 'kb-1'
        assert json.loads(create_result.stdout)['id'] == 'kb-new'
        search = json.loads(search_result.stdout)
        assert search['payload']['collection_name'] == 'kb-1'
        assert search['payload']['k'] == 3

    def test_admin_users_and_config(self):
        server, base_url = _serve_openwebui_like_api()
        try:
            users_result = self._run(['--json', '--base-url', base_url, 'admin', 'users'])
            config_result = self._run(['--json', '--base-url', base_url, 'admin', 'config'])
        finally:
            server.shutdown()

        assert json.loads(users_result.stdout)[0]['role'] == 'admin'
        assert json.loads(config_result.stdout)['ENABLE_SIGNUP'] is True

    def test_http_errors_use_stable_exit_codes(self):
        server, base_url = _serve_openwebui_like_api()
        try:
            auth_result = self._run(['--json', '--base-url', base_url, 'api', 'get', '/api/v1/private'], check=False)
            server_result = self._run(['--json', '--base-url', base_url, 'api', 'get', '/api/v1/broken'], check=False)
        finally:
            server.shutdown()

        assert auth_result.returncode == 3
        assert json.loads(auth_result.stdout)['exit_code'] == 3
        assert server_result.returncode == 5
        assert json.loads(server_result.stdout)['exit_code'] == 5

    def test_memories_commands(self):
        server, base_url = _serve_openwebui_like_api()
        try:
            list_result = self._run(['--json', '--base-url', base_url, 'memories', 'list'])
            add_result = self._run(['--json', '--base-url', base_url, 'memories', 'add', '--content', 'Remember X'])
            query_result = self._run(
                ['--json', '--base-url', base_url, 'memories', 'query', '--content', 'style', '--top-k', '3']
            )
            update_result = self._run(
                ['--json', '--base-url', base_url, 'memories', 'update', 'mem-1', '--content', 'Updated']
            )
            delete_result = self._run(['--json', '--base-url', base_url, 'memories', 'delete', 'mem-1'])
            reset_result = self._run(['--json', '--base-url', base_url, 'memories', 'reset'])
            clear_result = self._run(['--json', '--base-url', base_url, 'memories', 'clear'])
        finally:
            server.shutdown()

        assert json.loads(list_result.stdout)[0]['id'] == 'mem-1'
        assert json.loads(add_result.stdout)['payload'] == {'content': 'Remember X'}
        assert json.loads(query_result.stdout)['payload'] == {'content': 'style', 'k': 3}
        assert json.loads(update_result.stdout)['content'] == 'Updated'
        assert json.loads(delete_result.stdout) is True
        assert json.loads(reset_result.stdout) is True
        assert json.loads(clear_result.stdout) is True

    def test_notes_commands(self):
        server, base_url = _serve_openwebui_like_api()
        grants = '[{"principal_type":"user","principal_id":"user-2","permission":"read"}]'
        try:
            list_result = self._run(['--json', '--base-url', base_url, 'notes', 'list', '--page', '2'])
            pinned_result = self._run(['--json', '--base-url', base_url, 'notes', 'list', '--pinned'])
            search_result = self._run(
                [
                    '--json',
                    '--base-url',
                    base_url,
                    'notes',
                    'search',
                    '--query',
                    'deploy',
                    '--order-by',
                    'updated_at',
                    '--direction',
                    'asc',
                ]
            )
            create_result = self._run(
                [
                    '--json',
                    '--base-url',
                    base_url,
                    'notes',
                    'create',
                    '--title',
                    'Runbook',
                    '--data',
                    '{"content":{"md":"hello"}}',
                ]
            )
            update_result = self._run(
                [
                    '--json',
                    '--base-url',
                    base_url,
                    'notes',
                    'update',
                    'note-1',
                    '--title',
                    'Updated',
                    '--meta',
                    '{"source":"cli"}',
                ]
            )
            access_result = self._run(
                ['--json', '--base-url', base_url, 'notes', 'access', 'set', 'note-1', '--access-grants', grants]
            )
            pin_result = self._run(['--json', '--base-url', base_url, 'notes', 'pin', 'note-1'])
            delete_result = self._run(['--json', '--base-url', base_url, 'notes', 'delete', 'note-1'])
        finally:
            server.shutdown()

        assert json.loads(list_result.stdout)[0]['query'] == {'page': '2'}
        assert json.loads(pinned_result.stdout)[0]['is_pinned'] is True
        assert json.loads(search_result.stdout)['items'][0]['query']['query'] == 'deploy'
        assert json.loads(create_result.stdout)['payload']['data'] == {'content': {'md': 'hello'}}
        assert json.loads(update_result.stdout)['payload']['meta'] == {'source': 'cli'}
        assert json.loads(access_result.stdout)['payload']['access_grants'][0]['principal_id'] == 'user-2'
        assert json.loads(pin_result.stdout)['is_pinned'] is True
        assert json.loads(delete_result.stdout) is True

    def test_prompts_commands(self):
        server, base_url = _serve_openwebui_like_api()
        try:
            list_result = self._run(
                [
                    '--json',
                    '--base-url',
                    base_url,
                    'prompts',
                    'list',
                    '--page',
                    '2',
                    '--query',
                    'sum',
                    '--tag',
                    'writing',
                    '--order-by',
                    'updated_at',
                    '--direction',
                    'desc',
                ]
            )
            tags_result = self._run(['--json', '--base-url', base_url, 'prompts', 'tags'])
            show_result = self._run(['--json', '--base-url', base_url, 'prompts', 'show', 'prompt-1'])
            create_result = self._run(
                [
                    '--json',
                    '--base-url',
                    base_url,
                    'prompts',
                    'create',
                    '--command',
                    '/summarize',
                    '--name',
                    'Summarize',
                    '--content',
                    'Summarize {{text}}',
                    '--tag',
                    'writing',
                    '--data',
                    '{"variables":["text"]}',
                    '--meta',
                    '{"description":"short"}',
                ]
            )
            update_meta_result = self._run(
                [
                    '--json',
                    '--base-url',
                    base_url,
                    'prompts',
                    'update-meta',
                    'prompt-1',
                    '--command',
                    '/sum',
                    '--name',
                    'Sum',
                    '--tag',
                    'writing',
                ]
            )
            version_result = self._run(
                ['--json', '--base-url', base_url, 'prompts', 'version', 'prompt-1', '--version-id', 'hist-2']
            )
            toggle_result = self._run(['--json', '--base-url', base_url, 'prompts', 'toggle', 'prompt-1'])
            history_result = self._run(
                ['--json', '--base-url', base_url, 'prompts', 'history', 'list', 'prompt-1', '--page', '1']
            )
            diff_result = self._run(
                [
                    '--json',
                    '--base-url',
                    base_url,
                    'prompts',
                    'history',
                    'diff',
                    'prompt-1',
                    '--from-id',
                    'hist-1',
                    '--to-id',
                    'hist-2',
                ]
            )
            delete_history_result = self._run(
                ['--json', '--base-url', base_url, 'prompts', 'history', 'delete', 'prompt-1', 'hist-2']
            )
            delete_result = self._run(['--json', '--base-url', base_url, 'prompts', 'delete', 'prompt-1'])
        finally:
            server.shutdown()

        assert json.loads(list_result.stdout)['items'][0]['query']['tag'] == 'writing'
        assert json.loads(tags_result.stdout) == ['writing', 'support']
        assert json.loads(show_result.stdout)['write_access'] is True
        assert json.loads(create_result.stdout)['payload']['data'] == {'variables': ['text']}
        assert json.loads(update_meta_result.stdout)['payload'] == {'name': 'Sum', 'command': '/sum', 'tags': ['writing']}
        assert json.loads(version_result.stdout)['version_id'] == 'hist-2'
        assert json.loads(toggle_result.stdout)['is_active'] is False
        assert json.loads(history_result.stdout)[0]['query'] == {'page': '1'}
        assert json.loads(diff_result.stdout)['content_diff'] == ['-old', '+new']
        assert json.loads(delete_history_result.stdout) is True
        assert json.loads(delete_result.stdout) is True

    def test_automations_commands(self):
        server, base_url = _serve_openwebui_like_api()
        update_payload = '{"name":"Daily summary","data":{"prompt":"Summarize","model_id":"gpt-4.1","rrule":"FREQ=DAILY"},"is_active":true}'
        try:
            list_result = self._run(
                ['--json', '--base-url', base_url, 'automations', 'list', '--query', 'daily', '--status', 'active']
            )
            show_result = self._run(['--json', '--base-url', base_url, 'automations', 'show', 'auto-1'])
            create_result = self._run(
                [
                    '--json',
                    '--base-url',
                    base_url,
                    'automations',
                    'create',
                    '--name',
                    'Daily summary',
                    '--prompt',
                    'Summarize',
                    '--model',
                    'gpt-4.1',
                    '--rrule',
                    'FREQ=DAILY',
                ]
            )
            update_result = self._run(
                ['--json', '--base-url', base_url, 'automations', 'update', 'auto-1', '--data', update_payload]
            )
            toggle_result = self._run(['--json', '--base-url', base_url, 'automations', 'toggle', 'auto-1'])
            run_result = self._run(['--json', '--base-url', base_url, 'automations', 'run', 'auto-1'])
            runs_result = self._run(
                ['--json', '--base-url', base_url, 'automations', 'runs', 'auto-1', '--skip', '5', '--limit', '10']
            )
            delete_result = self._run(['--json', '--base-url', base_url, 'automations', 'delete', 'auto-1'])
        finally:
            server.shutdown()

        assert json.loads(list_result.stdout)['items'][0]['query']['status'] == 'active'
        assert json.loads(show_result.stdout)['id'] == 'auto-1'
        assert json.loads(create_result.stdout)['payload']['data']['rrule'] == 'FREQ=DAILY'
        assert json.loads(update_result.stdout)['payload']['is_active'] is True
        assert json.loads(toggle_result.stdout)['is_active'] is False
        assert json.loads(run_result.stdout)['status'] == 'queued'
        assert json.loads(runs_result.stdout)[0]['query'] == {'skip': '5', 'limit': '10'}
        assert json.loads(delete_result.stdout) is True
