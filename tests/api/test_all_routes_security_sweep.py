from __future__ import annotations

import pytest

pytestmark = pytest.mark.api

SAMPLE_VALUES = {
    "api_key_uuid": "api-key-1",
    "invoice_uid": "invoice-1",
    "org_id": "org-1",
    "payment_method_id": "pm_123",
    "project_id": "11111111-1111-1111-1111-111111111111",
    "project_uuid": "11111111-1111-1111-1111-111111111111",
    "setup_intent_id": "seti_123",
    "transaction_uid": "txn-1",
    "user_id": "user-1",
}


def _sample_path(path: str) -> str:
    sampled = path
    for name, value in SAMPLE_VALUES.items():
        sampled = sampled.replace("{" + name + "}", value)
    return sampled


def _management_operations(openapi: dict) -> list[tuple[str, str]]:
    operations = []
    for path, methods in sorted(openapi["paths"].items()):
        for method in sorted(methods):
            if method in {"get", "post", "put", "patch", "delete"}:
                operations.append((method.upper(), path))
    return operations


def _management_operations_requiring_security(openapi: dict) -> list[tuple[str, str]]:
    return [
        (method, path)
        for method, path in _management_operations(openapi)
        if openapi["paths"][path][method.lower()].get("security")
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        operation
        for operation in _management_operations_requiring_security(
            pytest.importorskip("gantry.management").management_app.openapi()
        )
    ],
)
async def test_protected_management_operations_reject_missing_auth(
    api_client,
    method: str,
    path: str,
) -> None:
    response = await api_client.request(
        method,
        _sample_path(path),
        json={},
    )

    assert response.status_code in {401, 403, 422}
    assert response.status_code < 500
