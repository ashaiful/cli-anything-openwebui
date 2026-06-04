from typing import Any

from cli_anything.openwebui.utils.openwebui_backend import OpenWebUIClient


def list_users(client: OpenWebUIClient) -> Any:
    return client.get('/api/v1/users/')


def all_users(client: OpenWebUIClient) -> Any:
    return client.get('/api/v1/users/all')


def search_users(client: OpenWebUIClient, query: str) -> Any:
    return client.get('/api/v1/users/search', params={'query': query})


def current_user_info(client: OpenWebUIClient) -> Any:
    return client.get('/api/v1/users/user/info')

