from typing import Any

from cli_anything.openwebui.utils.openwebui_backend import OpenWebUIClient


def signin(client: OpenWebUIClient, email: str, password: str) -> dict[str, Any]:
    return client.post('/api/v1/auths/signin', {'email': email, 'password': password})


def signup(client: OpenWebUIClient, name: str, email: str, password: str) -> dict[str, Any]:
    return client.post('/api/v1/auths/signup', {'name': name, 'email': email, 'password': password})


def me(client: OpenWebUIClient) -> dict[str, Any]:
    return client.get('/api/v1/auths/')


def api_key_create(client: OpenWebUIClient) -> dict[str, Any]:
    return client.post('/api/v1/auths/api_key')


def api_key_get(client: OpenWebUIClient) -> dict[str, Any]:
    return client.get('/api/v1/auths/api_key')


def api_key_delete(client: OpenWebUIClient) -> Any:
    return client.delete('/api/v1/auths/api_key')

