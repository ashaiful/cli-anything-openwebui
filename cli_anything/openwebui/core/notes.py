from typing import Any

from cli_anything.openwebui.utils.openwebui_backend import OpenWebUIClient


def list_notes(client: OpenWebUIClient, page: int | None = None) -> Any:
    params = {}
    if page is not None:
        params['page'] = page
    return client.get('/api/v1/notes/', params=params)


def list_pinned_notes(client: OpenWebUIClient) -> Any:
    return client.get('/api/v1/notes/pinned')


def search_notes(
    client: OpenWebUIClient,
    query: str | None = None,
    view_option: str | None = None,
    permission: str | None = None,
    order_by: str | None = None,
    direction: str | None = None,
    page: int | None = 1,
) -> Any:
    params = {}
    if query:
        params['query'] = query
    if view_option:
        params['view_option'] = view_option
    if permission:
        params['permission'] = permission
    if order_by:
        params['order_by'] = order_by
    if direction:
        params['direction'] = direction
    if page is not None:
        params['page'] = page
    return client.get('/api/v1/notes/search', params=params)


def show_note(client: OpenWebUIClient, note_id: str) -> Any:
    return client.get(f'/api/v1/notes/{note_id}')


def create_note(
    client: OpenWebUIClient,
    title: str,
    data: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    access_grants: list[dict[str, Any]] | None = None,
) -> Any:
    return client.post('/api/v1/notes/create', _payload(title, data, meta, access_grants))


def update_note(
    client: OpenWebUIClient,
    note_id: str,
    title: str,
    data: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    access_grants: list[dict[str, Any]] | None = None,
) -> Any:
    return client.post(f'/api/v1/notes/{note_id}/update', _payload(title, data, meta, access_grants))


def update_note_access(client: OpenWebUIClient, note_id: str, access_grants: list[dict[str, Any]]) -> Any:
    return client.post(f'/api/v1/notes/{note_id}/access/update', {'access_grants': access_grants})


def pin_note(client: OpenWebUIClient, note_id: str) -> Any:
    return client.post(f'/api/v1/notes/{note_id}/pin')


def delete_note(client: OpenWebUIClient, note_id: str) -> Any:
    return client.delete(f'/api/v1/notes/{note_id}/delete')


def _payload(
    title: str,
    data: dict[str, Any] | None,
    meta: dict[str, Any] | None,
    access_grants: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    return {
        'title': title,
        'data': data or {},
        'meta': meta or {},
        'access_grants': access_grants or [],
    }
