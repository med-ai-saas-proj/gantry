from __future__ import annotations

import pytest

from tests.api.fakes import TRANSACTION_UUID

pytestmark = pytest.mark.api

AUTH = {"Authorization": "Bearer admin-token", "X-Api-Key": "sk_test"}
API_KEY_UUID = "77777777-7777-7777-7777-777777777777"
AMOUNT = {"value": 1234, "scale": 2}


@pytest.mark.asyncio
async def test_internal_health_route_is_public_and_lightweight(internal_client) -> None:
    response = await internal_client.get("/ready")

    assert response.status_code == 200
    assert response.content == b""


@pytest.mark.asyncio
async def test_internal_usage_transaction_routes_delegate_to_billing_service(
    internal_client,
    authenticated_internal_api,
) -> None:
    posted = await internal_client.post(
        "/billing/",
        headers={**AUTH, "idempotency-key": "idem-1"},
        json={
            "api_key_uuid": API_KEY_UUID,
            "amount": AMOUNT,
            "details": {"usage": 1},
            "capture": False,
        },
    )
    captured = await internal_client.post(
        f"/billing/{TRANSACTION_UUID}/capture",
        headers=AUTH,
        json={"real_amount": AMOUNT},
    )

    assert posted.status_code == 200
    assert posted.json() == TRANSACTION_UUID
    assert captured.status_code == 200
    assert captured.json() is True
    assert authenticated_internal_api["billing_transaction"].calls[0][0] == "post"
    assert str(
        authenticated_internal_api["billing_transaction"].calls[0][1][
            "req"
        ].api_key_uuid
    ) == API_KEY_UUID


@pytest.mark.asyncio
async def test_internal_usage_transaction_validation_rejects_bad_amount(
    internal_client,
    authenticated_internal_api,
) -> None:
    response = await internal_client.post(
        "/billing/",
        headers=AUTH,
        json={"api_key_uuid": API_KEY_UUID, "amount": "bad"},
    )

    assert response.status_code in {400, 422}
