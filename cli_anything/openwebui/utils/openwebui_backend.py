from __future__ import annotations

from typing import Any, Callable

import requests


Transport = Callable[..., Any]


class OpenWebUIClient:
    """Small HTTP client for a running OpenWebUI FastAPI backend."""

    def __init__(
        self,
        base_url: str = 'http://localhost:8080',
        token: str | None = None,
        timeout: int = 30,
        transport: Transport | None = None,
    ):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.timeout = timeout
        self.transport = transport or requests.request

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return self.request('GET', endpoint, params=params)

    def post(self, endpoint: str, data: dict[str, Any] | None = None) -> Any:
        return self.request('POST', endpoint, json=data or {})

    def delete(self, endpoint: str, data: dict[str, Any] | None = None) -> Any:
        kwargs: dict[str, Any] = {}
        if data is not None:
            kwargs['json'] = data
        return self.request('DELETE', endpoint, **kwargs)

    def upload(self, endpoint: str, path: str) -> Any:
        with open(path, 'rb') as fh:
            return self.request('POST', endpoint, files={'file': fh})

    def request(self, method: str, endpoint: str, **kwargs) -> Any:
        path = endpoint if endpoint.startswith('/') else f'/{endpoint}'
        url = f'{self.base_url}{path}'
        headers = dict(kwargs.pop('headers', {}) or {})
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        if 'files' not in kwargs:
            headers.setdefault('Content-Type', 'application/json')
        try:
            response = self.transport(method, url, headers=headers, timeout=self.timeout, **kwargs)
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                f'Cannot connect to OpenWebUI at {self.base_url}. Start it with `open-webui serve` '
                'or pass --base-url for an existing deployment.'
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(f'Request to OpenWebUI timed out: {method} {path}') from exc

        status_code = getattr(response, 'status_code', 0)
        content = getattr(response, 'content', b'')
        text = getattr(response, 'text', '')
        if status_code >= 400:
            raise RuntimeError(f'OpenWebUI API error {status_code} on {method} {path}: {text}')
        if status_code == 204 or not content:
            return {'status': 'ok'}

        content_type = getattr(response, 'headers', {}).get('content-type', '')
        if 'application/json' in content_type:
            try:
                return response.json()
            except ValueError:
                return {'status': 'ok', 'text': text}
        return {'status': 'ok', 'text': text.strip()}

