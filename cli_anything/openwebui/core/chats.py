from typing import Any

from cli_anything.openwebui.utils.openwebui_backend import OpenWebUIClient


def list_chats(client: OpenWebUIClient, page: int | None = None) -> Any:
    params = {}
    if page is not None:
        params['page'] = page
    return client.get('/api/v1/chats/list', params=params)


def show_chat(client: OpenWebUIClient, chat_id: str) -> Any:
    return client.get(f'/api/v1/chats/{chat_id}')


def create_chat(client: OpenWebUIClient, title: str, chat: dict[str, Any] | None = None) -> Any:
    payload = {'chat': chat or {'title': title}}
    return client.post('/api/v1/chats/new', payload)


def update_chat(client: OpenWebUIClient, chat_id: str, chat: dict[str, Any]) -> Any:
    return client.post(f'/api/v1/chats/{chat_id}', {'chat': chat})


def delete_chat(client: OpenWebUIClient, chat_id: str) -> Any:
    return client.delete(f'/api/v1/chats/{chat_id}')


def pin_chat(client: OpenWebUIClient, chat_id: str) -> Any:
    return client.post(f'/api/v1/chats/{chat_id}/pin')


def archive_chat(client: OpenWebUIClient, chat_id: str) -> Any:
    return client.post(f'/api/v1/chats/{chat_id}/archive')


def clone_chat(client: OpenWebUIClient, chat_id: str, title: str | None = None) -> Any:
    return client.post(f'/api/v1/chats/{chat_id}/clone', {'title': title})


def share_chat(client: OpenWebUIClient, chat_id: str) -> Any:
    return client.post(f'/api/v1/chats/{chat_id}/share')


def add_tag(client: OpenWebUIClient, chat_id: str, name: str) -> Any:
    return client.post(f'/api/v1/chats/{chat_id}/tags', {'name': name})


def remove_tag(client: OpenWebUIClient, chat_id: str, name: str) -> Any:
    return client.delete(f'/api/v1/chats/{chat_id}/tags', {'name': name})

