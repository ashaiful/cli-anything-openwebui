from typing import Any

from cli_anything.openwebui.utils.openwebui_backend import OpenWebUIClient


def list_prompts(
    client: OpenWebUIClient,
    page: int = 1,
    query: str | None = None,
    view_option: str | None = None,
    tag: str | None = None,
    order_by: str | None = None,
    direction: str | None = None,
) -> Any:
    params = {'page': page}
    if query:
        params['query'] = query
    if view_option:
        params['view_option'] = view_option
    if tag:
        params['tag'] = tag
    if order_by:
        params['order_by'] = order_by
    if direction:
        params['direction'] = direction
    return client.get('/api/v1/prompts/list', params=params)


def show_prompt(client: OpenWebUIClient, prompt_id: str) -> Any:
    return client.get(f'/api/v1/prompts/id/{prompt_id}')


def tags(client: OpenWebUIClient) -> Any:
    return client.get('/api/v1/prompts/tags')


def create_prompt(client: OpenWebUIClient, payload: dict[str, Any]) -> Any:
    return client.post('/api/v1/prompts/create', payload)


def update_prompt(client: OpenWebUIClient, prompt_id: str, payload: dict[str, Any]) -> Any:
    return client.post(f'/api/v1/prompts/id/{prompt_id}/update', payload)


def update_prompt_metadata(
    client: OpenWebUIClient,
    prompt_id: str,
    *,
    name: str,
    command: str,
    tags: list[str | None] | None = None,
) -> Any:
    return client.post(f'/api/v1/prompts/id/{prompt_id}/update/meta', {'name': name, 'command': command, 'tags': tags or []})


def set_prompt_version(client: OpenWebUIClient, prompt_id: str, version_id: str) -> Any:
    return client.post(f'/api/v1/prompts/id/{prompt_id}/update/version', {'version_id': version_id})


def toggle_prompt(client: OpenWebUIClient, prompt_id: str) -> Any:
    return client.post(f'/api/v1/prompts/id/{prompt_id}/toggle')


def delete_prompt(client: OpenWebUIClient, prompt_id: str) -> Any:
    return client.delete(f'/api/v1/prompts/id/{prompt_id}/delete')


def list_prompt_history(client: OpenWebUIClient, prompt_id: str, page: int = 0) -> Any:
    return client.get(f'/api/v1/prompts/id/{prompt_id}/history', params={'page': page})


def show_prompt_history(client: OpenWebUIClient, prompt_id: str, history_id: str) -> Any:
    return client.get(f'/api/v1/prompts/id/{prompt_id}/history/{history_id}')


def delete_prompt_history(client: OpenWebUIClient, prompt_id: str, history_id: str) -> Any:
    return client.delete(f'/api/v1/prompts/id/{prompt_id}/history/{history_id}')


def diff_prompt_history(client: OpenWebUIClient, prompt_id: str, from_id: str, to_id: str) -> Any:
    return client.get(f'/api/v1/prompts/id/{prompt_id}/history/diff', params={'from_id': from_id, 'to_id': to_id})
