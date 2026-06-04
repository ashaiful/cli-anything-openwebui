from typing import Any

from cli_anything.openwebui.utils.openwebui_backend import OpenWebUIClient


def list_automations(
    client: OpenWebUIClient,
    query: str | None = None,
    status: str | None = None,
    page: int = 1,
) -> Any:
    params = {'page': page}
    if query:
        params['query'] = query
    if status:
        params['status'] = status
    return client.get('/api/v1/automations/list', params=params)


def show_automation(client: OpenWebUIClient, automation_id: str) -> Any:
    return client.get(f'/api/v1/automations/{automation_id}')


def create_automation(client: OpenWebUIClient, payload: dict[str, Any]) -> Any:
    return client.post('/api/v1/automations/create', payload)


def update_automation(client: OpenWebUIClient, automation_id: str, payload: dict[str, Any]) -> Any:
    return client.post(f'/api/v1/automations/{automation_id}/update', payload)


def toggle_automation(client: OpenWebUIClient, automation_id: str) -> Any:
    return client.post(f'/api/v1/automations/{automation_id}/toggle')


def run_automation(client: OpenWebUIClient, automation_id: str) -> Any:
    return client.post(f'/api/v1/automations/{automation_id}/run')


def delete_automation(client: OpenWebUIClient, automation_id: str) -> Any:
    return client.delete(f'/api/v1/automations/{automation_id}/delete')


def list_automation_runs(client: OpenWebUIClient, automation_id: str, skip: int = 0, limit: int = 50) -> Any:
    return client.get(f'/api/v1/automations/{automation_id}/runs', params={'skip': skip, 'limit': limit})
