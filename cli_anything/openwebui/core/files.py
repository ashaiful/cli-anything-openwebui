from typing import Any

from cli_anything.openwebui.utils.openwebui_backend import OpenWebUIClient


def list_files(client: OpenWebUIClient) -> Any:
    return client.get('/api/v1/files/')


def show_file(client: OpenWebUIClient, file_id: str) -> Any:
    return client.get(f'/api/v1/files/{file_id}')


def upload_file(client: OpenWebUIClient, path: str) -> Any:
    return client.upload('/api/v1/files/', path)


def delete_file(client: OpenWebUIClient, file_id: str) -> Any:
    return client.delete(f'/api/v1/files/{file_id}')


def content(client: OpenWebUIClient, file_id: str) -> Any:
    return client.get(f'/api/v1/files/{file_id}/content')

