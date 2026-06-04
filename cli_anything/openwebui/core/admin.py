from typing import Any

from cli_anything.openwebui.utils.openwebui_backend import OpenWebUIClient


def stats(client: OpenWebUIClient) -> dict[str, Any]:
    user = client.get('/api/v1/auths/')
    return {'connected': True, 'user': user}


def users(client: OpenWebUIClient) -> Any:
    return client.get('/api/v1/users/')


def config(client: OpenWebUIClient) -> Any:
    return client.get('/api/v1/auths/admin/config')
