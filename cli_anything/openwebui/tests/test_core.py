import json

import pytest

from cli_anything.openwebui.core.session import SessionState
from cli_anything.openwebui.utils import token_store
from cli_anything.openwebui.utils.openwebui_backend import OpenWebUIClient


class FakeResponse:
    def __init__(self, status_code=200, content=b'{}', text='{}', headers=None):
        self.status_code = status_code
        self.content = content
        self.text = text
        self.headers = headers or {'content-type': 'application/json'}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError('http error')

    def json(self):
        return json.loads(self.text)


def test_session_empty_has_no_auth_or_selected_chat():
    state = SessionState.empty()

    assert state.base_url == 'http://localhost:8080'
    assert state.token is None
    assert state.current_chat_id is None
    assert state.undo_stack == []
    assert state.redo_stack == []
    assert state.profiles == {}
    assert state.default_profile is None


def test_profile_set_and_apply_updates_base_url_and_token():
    state = SessionState.empty()

    state.set_profile('prod', base_url='https://prod.example.com', token='prod-token', make_default=True)
    applied = state.apply_profile('prod')

    assert applied is True
    assert state.base_url == 'https://prod.example.com'
    assert state.token == 'prod-token'
    assert state.default_profile == 'prod'


def test_profile_apply_missing_profile_returns_false():
    state = SessionState.empty()

    assert state.apply_profile('missing') is False


def test_masked_hides_tokens_in_profiles_and_history():
    state = SessionState.empty()
    state.token = 'active-token'
    state.profiles['prod'] = {'base_url': 'https://prod.example.com', 'token': 'profile-token'}
    state.undo_stack.append({'base_url': 'https://prod.example.com', 'token': 'undo-token'})
    state.redo_stack.append({'base_url': 'https://prod.example.com', 'token': 'redo-token'})

    masked = state.masked()

    assert masked['token'] == '***'
    assert masked['profiles']['prod']['token'] == '***'
    assert masked['undo_stack'][0]['token'] == '***'
    assert masked['redo_stack'][0]['token'] == '***'


def test_select_chat_records_undo_history():
    state = SessionState.empty()

    state.select_chat('chat-1')
    state.select_chat('chat-2')

    assert state.current_chat_id == 'chat-2'
    assert state.undo_stack[-1]['current_chat_id'] == 'chat-1'
    assert state.redo_stack == []


def test_undo_restores_previous_selected_chat():
    state = SessionState.empty()
    state.select_chat('chat-1')
    state.select_chat('chat-2')

    restored = state.undo()

    assert restored is True
    assert state.current_chat_id == 'chat-1'
    assert state.redo_stack[-1]['current_chat_id'] == 'chat-2'


def test_redo_reapplies_selected_chat():
    state = SessionState.empty()
    state.select_chat('chat-1')
    state.select_chat('chat-2')
    state.undo()

    restored = state.redo()

    assert restored is True
    assert state.current_chat_id == 'chat-2'


def test_client_sends_bearer_token_header():
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return FakeResponse(text='{"ok": true}', content=b'{"ok": true}')

    client = OpenWebUIClient('http://owui.local', token='secret-token', transport=transport)

    assert client.get('/api/v1/models/tags') == {'ok': True}
    assert calls[0][2]['headers']['Authorization'] == 'Bearer secret-token'


def test_client_handles_empty_response():
    def transport(method, url, **kwargs):
        return FakeResponse(status_code=204, content=b'', text='', headers={})

    client = OpenWebUIClient('http://owui.local', transport=transport)

    assert client.delete('/api/v1/chats/chat-1') == {'status': 'ok'}


def test_client_http_error_mentions_method_endpoint_status_and_body():
    def transport(method, url, **kwargs):
        return FakeResponse(status_code=401, content=b'nope', text='nope')

    client = OpenWebUIClient('http://owui.local', transport=transport)

    with pytest.raises(RuntimeError) as err:
        client.get('/api/v1/auths/')

    message = str(err.value)
    assert 'GET /api/v1/auths/' in message
    assert '401' in message
    assert 'nope' in message


def test_client_returns_text_payload_for_non_json_response():
    def transport(method, url, **kwargs):
        return FakeResponse(content=b'Open WebUI', text='Open WebUI', headers={'content-type': 'text/plain'})

    client = OpenWebUIClient('http://owui.local', transport=transport)

    assert client.get('/') == {'status': 'ok', 'text': 'Open WebUI'}


def test_token_store_uses_keyring_when_available(monkeypatch):
    stored = {}

    class FakeKeyring:
        class errors:
            class KeyringError(Exception):
                pass

            class PasswordDeleteError(Exception):
                pass

        @staticmethod
        def set_password(service, key, token):
            stored[(service, key)] = token

        @staticmethod
        def get_password(service, key):
            return stored.get((service, key))

        @staticmethod
        def delete_password(service, key):
            stored.pop((service, key), None)

    monkeypatch.setitem(__import__('sys').modules, 'keyring', FakeKeyring)

    assert token_store.set_token('prod', 'https://prod.example.com', 'secret') is True
    assert token_store.get_token('prod', 'https://prod.example.com') == 'secret'
    assert token_store.delete_token('prod', 'https://prod.example.com') is True


def _capture_client():
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return FakeResponse(text='{"ok": true}', content=b'{"ok": true}')

    return OpenWebUIClient('http://owui.local', transport=transport), calls


def test_memories_core_maps_commands_to_http_endpoints():
    from cli_anything.openwebui.core import memories as memories_core

    client, calls = _capture_client()

    memories_core.list_memories(client)
    memories_core.add_memory(client, 'Remember concise answers')
    memories_core.query_memories(client, 'style', top_k=3)
    memories_core.update_memory(client, 'mem-1', 'Updated memory')
    memories_core.delete_memory(client, 'mem-1')
    memories_core.reset_memories(client)
    memories_core.clear_memories(client)

    assert [(method, url.replace('http://owui.local', '')) for method, url, _ in calls] == [
        ('GET', '/api/v1/memories/'),
        ('POST', '/api/v1/memories/add'),
        ('POST', '/api/v1/memories/query'),
        ('POST', '/api/v1/memories/mem-1/update'),
        ('DELETE', '/api/v1/memories/mem-1'),
        ('POST', '/api/v1/memories/reset'),
        ('DELETE', '/api/v1/memories/delete/user'),
    ]
    assert calls[1][2]['json'] == {'content': 'Remember concise answers'}
    assert calls[2][2]['json'] == {'content': 'style', 'k': 3}
    assert calls[3][2]['json'] == {'content': 'Updated memory'}


def test_notes_core_maps_search_and_mutation_payloads():
    from cli_anything.openwebui.core import notes as notes_core

    client, calls = _capture_client()
    grants = [{'principal_type': 'user', 'principal_id': 'user-2', 'permission': 'read'}]

    notes_core.list_notes(client, page=2)
    notes_core.search_notes(client, query='deploy', view_option='created', permission='read', order_by='updated_at', direction='asc', page=1)
    notes_core.create_note(client, 'Runbook', data={'content': {'md': 'hello'}}, meta={'source': 'cli'}, access_grants=grants)
    notes_core.update_note(client, 'note-1', 'Updated', meta={'source': 'cli'})
    notes_core.update_note_access(client, 'note-1', grants)
    notes_core.pin_note(client, 'note-1')
    notes_core.delete_note(client, 'note-1')

    assert calls[0][0] == 'GET'
    assert calls[0][1].endswith('/api/v1/notes/')
    assert calls[0][2]['params'] == {'page': 2}
    assert calls[1][2]['params'] == {
        'query': 'deploy',
        'view_option': 'created',
        'permission': 'read',
        'order_by': 'updated_at',
        'direction': 'asc',
        'page': 1,
    }
    assert calls[2][2]['json'] == {
        'title': 'Runbook',
        'data': {'content': {'md': 'hello'}},
        'meta': {'source': 'cli'},
        'access_grants': grants,
    }
    assert calls[3][1].endswith('/api/v1/notes/note-1/update')
    assert calls[3][2]['json'] == {'title': 'Updated', 'data': {}, 'meta': {'source': 'cli'}, 'access_grants': []}
    assert calls[4][2]['json'] == {'access_grants': grants}
    assert calls[5][1].endswith('/api/v1/notes/note-1/pin')
    assert calls[6][0] == 'DELETE'
    assert calls[6][1].endswith('/api/v1/notes/note-1/delete')


def test_prompts_core_maps_history_and_payload_commands():
    from cli_anything.openwebui.core import prompts as prompts_core

    client, calls = _capture_client()
    payload = {'command': '/sum', 'name': 'Summarize', 'content': 'Summarize {{text}}'}

    prompts_core.list_prompts(client, page=2, query='sum', tag='writing', order_by='updated_at', direction='desc')
    prompts_core.tags(client)
    prompts_core.show_prompt(client, 'prompt-1')
    prompts_core.create_prompt(client, payload)
    prompts_core.update_prompt(client, 'prompt-1', payload)
    prompts_core.update_prompt_metadata(client, 'prompt-1', name='Sum', command='/sum', tags=['writing'])
    prompts_core.set_prompt_version(client, 'prompt-1', 'hist-2')
    prompts_core.toggle_prompt(client, 'prompt-1')
    prompts_core.list_prompt_history(client, 'prompt-1', page=1)
    prompts_core.diff_prompt_history(client, 'prompt-1', from_id='hist-1', to_id='hist-2')
    prompts_core.delete_prompt_history(client, 'prompt-1', 'hist-2')
    prompts_core.delete_prompt(client, 'prompt-1')

    assert calls[0][1].endswith('/api/v1/prompts/list')
    assert calls[0][2]['params'] == {'page': 2, 'query': 'sum', 'tag': 'writing', 'order_by': 'updated_at', 'direction': 'desc'}
    assert calls[3][2]['json'] == payload
    assert calls[5][2]['json'] == {'name': 'Sum', 'command': '/sum', 'tags': ['writing']}
    assert calls[6][2]['json'] == {'version_id': 'hist-2'}
    assert calls[8][2]['params'] == {'page': 1}
    assert calls[9][2]['params'] == {'from_id': 'hist-1', 'to_id': 'hist-2'}
    assert calls[10][0] == 'DELETE'
    assert calls[11][1].endswith('/api/v1/prompts/id/prompt-1/delete')


def test_automations_core_maps_commands_to_http_endpoints():
    from cli_anything.openwebui.core import automations as automations_core

    client, calls = _capture_client()
    payload = {'name': 'Daily summary', 'data': {'prompt': 'Summarize', 'model_id': 'gpt-4.1', 'rrule': 'FREQ=DAILY'}}

    automations_core.list_automations(client, query='daily', status='active', page=2)
    automations_core.show_automation(client, 'auto-1')
    automations_core.create_automation(client, payload)
    automations_core.update_automation(client, 'auto-1', payload)
    automations_core.toggle_automation(client, 'auto-1')
    automations_core.run_automation(client, 'auto-1')
    automations_core.list_automation_runs(client, 'auto-1', skip=5, limit=10)
    automations_core.delete_automation(client, 'auto-1')

    assert calls[0][1].endswith('/api/v1/automations/list')
    assert calls[0][2]['params'] == {'page': 2, 'query': 'daily', 'status': 'active'}
    assert calls[1][1].endswith('/api/v1/automations/auto-1')
    assert calls[2][2]['json'] == payload
    assert calls[3][1].endswith('/api/v1/automations/auto-1/update')
    assert calls[4][1].endswith('/api/v1/automations/auto-1/toggle')
    assert calls[5][1].endswith('/api/v1/automations/auto-1/run')
    assert calls[6][2]['params'] == {'skip': 5, 'limit': 10}
    assert calls[7][0] == 'DELETE'
    assert calls[7][1].endswith('/api/v1/automations/auto-1/delete')
