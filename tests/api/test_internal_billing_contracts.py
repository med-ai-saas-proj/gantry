from __future__ import annotations

import pytest

from tests.api.fakes import INVOICE_UUID, TRANSACTION_UUID

pytestmark = pytest.mark.api

AUTH = {"Authorization": "Bearer admin-token", "X-Api-Key": "sk_test"}
AMOUNT = {"value": 1234, "scale": 2}


@pytest.mark.asyncio
async def test_internal_credit_routes_delegate_admin_context(internal_client, authenticated_internal_api) -> None:
    added = await internal_client.post(
        "/billing/credits",
        headers=AUTH,
        json={"org_id": "org-1", "amount": AMOUNT, "description": "promo"},
    )
    available = await internal_client.get("/billing/credits/org-1/available", headers=AUTH)
    transactions = await internal_client.get(
        "/billing/credits/org-1/transactions",
        headers=AUTH,
        params={"limit": 3, "offset": 2},
    )

    assert added.status_code == 200
    assert added.json()["data"]["amount"] == "47.00"
    assert available.json()["data"]["amount"] == "42.00"
    assert transactions.json()["limit"] == 3
    assert authenticated_internal_api["credit"].calls[0][0] == "addCredits"


@pytest.mark.asyncio
async def test_internal_invoice_routes_delegate_admin_context(internal_client, authenticated_internal_api) -> None:
    listed = await internal_client.get(
        "/billing/invoices",
        headers=AUTH,
        params={"org_ids": "org-1", "limit": 4, "offset": 1, "paid": False},
    )
    detail = await internal_client.get(f"/billing/invoices/{INVOICE_UUID}", headers=AUTH)
    paid = await internal_client.put(f"/billing/invoices/{INVOICE_UUID}/mark_paid", headers=AUTH)
    refunded = await internal_client.post(f"/billing/invoices/{INVOICE_UUID}/refund", headers=AUTH)

    assert listed.status_code == 200
    assert listed.json()["limit"] == 4
    assert detail.json()["data"]["invoice_uid"] == INVOICE_UUID
    assert paid.status_code == 200
    assert refunded.status_code == 200


@pytest.mark.asyncio
async def test_internal_usage_transaction_routes_use_api_key_context(internal_client, authenticated_internal_api) -> None:
    posted = await internal_client.post(
        "/billing/",
        headers={**AUTH, "idempotency-key": "idem-1"},
        json={"amount": AMOUNT, "details": {"usage": 1}, "capture": False},
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
    assert authenticated_internal_api["api_key"].calls[0] == ("getApiKeyInternalIds", "api-key-1")
    assert authenticated_internal_api["billing_transaction"].calls[0][0] == "post"
