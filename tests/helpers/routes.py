from __future__ import annotations

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}

SAMPLE_VALUES = {
    "api_key_uuid": "api-key-1",
    "conversation_uid": "33333333-3333-3333-3333-333333333333",
    "file_id": "22222222-2222-2222-2222-222222222222",
    "full_path": "v1/messages",
    "invoice_uid": "55555555-5555-5555-5555-555555555555",
    "invitation_id": "inv-1",
    "message_seq_id": "1",
    "org_id": "org-1",
    "payment_method_id": "pm_123",
    "project_id": "11111111-1111-1111-1111-111111111111",
    "project_uuid": "11111111-1111-1111-1111-111111111111",
    "route_name": "chat",
    "setup_intent_id": "seti_123",
    "task_id": "task-1",
    "transaction_uid": "44444444-4444-4444-4444-444444444444",
    "user_id": "user-1",
}


def operations(openapi: dict) -> list[tuple[str, str]]:
    return [
        (method.upper(), path)
        for path, methods in sorted(openapi["paths"].items())
        for method in sorted(methods)
        if method in HTTP_METHODS
    ]


def sample_path(path: str) -> str:
    sampled = path
    for name, value in SAMPLE_VALUES.items():
        sampled = sampled.replace("{" + name + "}", value)
    return sampled
