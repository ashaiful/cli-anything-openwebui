from typing import Any

from cli_anything.openwebui.utils.openwebui_backend import OpenWebUIClient


def status(client: OpenWebUIClient) -> dict[str, Any]:
    data = client.get('/')
    return {'connected': True, 'base_url': client.base_url, 'response': data}


def openapi(client: OpenWebUIClient) -> Any:
    return client.get('/openapi.json')


def version(client: OpenWebUIClient) -> dict[str, Any]:
    data = client.get('/api/version')
    return data if isinstance(data, dict) else {'version': data}

