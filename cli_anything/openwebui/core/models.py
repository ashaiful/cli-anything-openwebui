from typing import Any

from cli_anything.openwebui.utils.openwebui_backend import OpenWebUIClient


def list_models(client: OpenWebUIClient, page: int = 1, query: str | None = None) -> Any:
    params = {'page': page}
    if query:
        params['query'] = query
    return client.get('/api/v1/models/list', params=params)


def show_model(client: OpenWebUIClient, model_id: str) -> Any:
    return client.get('/api/v1/models/model', params={'id': model_id})


def tags(client: OpenWebUIClient) -> Any:
    return client.get('/api/v1/models/tags')


def base(client: OpenWebUIClient) -> Any:
    return client.get('/api/v1/models/base')


def export(client: OpenWebUIClient) -> Any:
    return client.get('/api/v1/models/export')

def sync(client: OpenWebUIClient, models_payload: list[dict]) -> Any:
    return client.post('/api/v1/models/sync', {'models': models_payload})

