from __future__ import annotations

import pytest

from tests.api.coverage_matrix import operations_with_request_body
from tests.helpers.routes import operations, sample_path

pytestmark = pytest.mark.api


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        operation
        for operation in operations(pytest.importorskip("gantry.service").service_app.openapi())
    ],
)
async def test_protected_service_operations_reject_missing_auth(
    service_client,
    method: str,
    path: str,
) -> None:
    response = await service_client.request(method, sample_path(path), json={})

    assert response.status_code in {401, 403, 422}
    assert response.status_code < 500


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        operation
        for operation in operations(pytest.importorskip("gantry.main.app").internal_app.openapi())
    ],
)
async def test_protected_internal_operations_reject_missing_auth(
    internal_client,
    method: str,
    path: str,
) -> None:
    response = await internal_client.request(method, sample_path(path), json={})

    assert response.status_code in {401, 403, 422}
    assert response.status_code < 500


@pytest.mark.asyncio
async def test_gateway_proxy_rejects_missing_api_key(gateway_client) -> None:
    response = await gateway_client.get("/chat/messages")

    assert response.status_code in {401, 403}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("post", "/v1/conversations/33333333-3333-3333-3333-333333333333/messages", {"messages": "bad"}),
        ("get", "/v1/conversations/not-a-uuid", None),
        ("post", "/v1/rag/service/query/text", {"top_k": 0, "query_text": "hello"}),
        ("post", "/billing/credits", {"org_id": "org-1", "amount": "bad"}),
    ],
)
async def test_cross_app_invalid_request_shapes_return_422(
    service_client,
    internal_client,
    authenticated_service_api,
    authenticated_internal_api,
    method: str,
    path: str,
    json_body: dict | None,
) -> None:
    client = internal_client if path.startswith("/billing") else service_client
    request_kwargs = {"headers": {"Authorization": "Bearer token", "X-Api-Key": "sk_test"}}
    if json_body is not None:
        request_kwargs["json"] = json_body
    response = await client.request(method.upper(), path, **request_kwargs)

    assert response.status_code in {400, 422}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("app_name", "method", "path"),
    [
        ("management", method, path)
        for method, path in operations_with_request_body(
            pytest.importorskip("gantry.management").management_app.openapi()
        )
    ]
    + [
        ("service", method, path)
        for method, path in operations_with_request_body(
            pytest.importorskip("gantry.service").service_app.openapi()
        )
    ]
    + [
        ("internal", method, path)
        for method, path in operations_with_request_body(
            pytest.importorskip("gantry.main.app").internal_app.openapi()
        )
    ],
)
async def test_body_operations_reject_malformed_json_without_5xx(
    api_client,
    service_client,
    internal_client,
    authenticated_api,
    authenticated_service_api,
    authenticated_internal_api,
    app_name: str,
    method: str,
    path: str,
) -> None:
    client = {
        "management": api_client,
        "service": service_client,
        "internal": internal_client,
    }[app_name]
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer token",
        "X-Api-Key": "sk_test",
        "stripe-signature": "invalid",
    }

    response = await client.request(
        method,
        sample_path(path),
        headers=headers,
        content=b"{",
    )

    assert response.status_code in {400, 415, 422}
    assert response.status_code < 500
