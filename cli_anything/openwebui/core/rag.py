from typing import Any

from cli_anything.openwebui.utils.openwebui_backend import OpenWebUIClient


def list_collections(client: OpenWebUIClient) -> Any:
    return client.get('/api/v1/knowledge/')


def create_collection(client: OpenWebUIClient, name: str, description: str = '') -> Any:
    return client.post('/api/v1/knowledge/create', {'name': name, 'description': description})


def delete_collection(client: OpenWebUIClient, collection_id: str) -> Any:
    return client.delete(f'/api/v1/knowledge/{collection_id}/delete')


def add_file(client: OpenWebUIClient, collection_id: str, file_id: str) -> Any:
    return client.post(f'/api/v1/knowledge/{collection_id}/file/add', {'file_id': file_id})


def remove_file(client: OpenWebUIClient, collection_id: str, file_id: str) -> Any:
    return client.post(f'/api/v1/knowledge/{collection_id}/file/remove', {'file_id': file_id})


def search_collection(client: OpenWebUIClient, collection_id: str, query: str, top_k: int = 5) -> Any:
    return client.post(
        '/api/v1/retrieval/query/collection',
        {'collection_name': collection_id, 'query': query, 'k': top_k},
    )

