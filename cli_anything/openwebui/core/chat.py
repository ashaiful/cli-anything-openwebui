from typing import Any

from cli_anything.openwebui.utils.openwebui_backend import OpenWebUIClient


def send_completion(
    client: OpenWebUIClient,
    model: str,
    prompt: str,
    system: str | None = None,
    chat_id: str | None = None,
    files: list[str] | None = None,
    collections: list[str] | None = None,
    stream: bool = False,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})

    payload: dict[str, Any] = {
        'model': model,
        'messages': messages,
        'stream': stream,
    }
    if chat_id:
        payload['chat_id'] = chat_id
    if temperature is not None:
        payload['temperature'] = temperature
    if max_tokens is not None:
        payload['max_tokens'] = max_tokens

    context_files = []
    for file_id in files or []:
        context_files.append({'type': 'file', 'id': file_id})
    for collection_id in collections or []:
        context_files.append({'type': 'collection', 'id': collection_id})
    if context_files:
        payload['files'] = context_files

    response = client.post('/api/chat/completions', payload)
    content = ''
    if isinstance(response, dict):
        choices = response.get('choices') or []
        if choices:
            content = choices[0].get('message', {}).get('content') or choices[0].get('delta', {}).get('content') or ''
    return {'content': content, 'response': response}

