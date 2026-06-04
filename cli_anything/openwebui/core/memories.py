from typing import Any

from cli_anything.openwebui.utils.openwebui_backend import OpenWebUIClient


def list_memories(client: OpenWebUIClient) -> Any:
    return client.get('/api/v1/memories/')


def add_memory(client: OpenWebUIClient, content: str) -> Any:
    return client.post('/api/v1/memories/add', {'content': content})


def query_memories(client: OpenWebUIClient, content: str, top_k: int = 1) -> Any:
    return client.post('/api/v1/memories/query', {'content': content, 'k': top_k})


def update_memory(client: OpenWebUIClient, memory_id: str, content: str) -> Any:
    return client.post(f'/api/v1/memories/{memory_id}/update', {'content': content})


def delete_memory(client: OpenWebUIClient, memory_id: str) -> Any:
    return client.delete(f'/api/v1/memories/{memory_id}')


def reset_memories(client: OpenWebUIClient) -> Any:
    return client.post('/api/v1/memories/reset')


def clear_memories(client: OpenWebUIClient) -> Any:
    return client.delete('/api/v1/memories/delete/user')
