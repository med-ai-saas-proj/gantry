from __future__ import annotations

import pytest

from tests.api.fakes import INVOICE_UUID, PROJECT_UUID, TRANSACTION_UUID

pytestmark = pytest.mark.api

AUTH = {"Authorization": "Bearer test-token"}
PERIOD_PARAMS = {
    "period_start": "2026-01-01T00:00:00Z",
    "period_end": "2026-01-31T00:00:00Z",
    "period": "daily",
}
ADDRESS = {
    "line1": "1 Main",
    "line2": "Suite 1",
    "city": "HCM",
    "state": "HCM",
    "postal_code": "70000",
    "country": "VN",
}


@pytest.mark.asyncio
async def test_billing_aggregate_routes_delegate_org_and_project_context(api_client, authenticated_api) -> None:
    org = await api_client.get("/v1/billing/aggregates/organizations", headers=AUTH, params=PERIOD_PARAMS)
    project = await api_client.get(
        "/v1/billing/aggregates/projects",
        headers=AUTH,
        params={**PERIOD_PARAMS, "project_uuids": PROJECT_UUID},
    )

    assert org.status_code == 200
    assert project.status_code == 200
    assert org.json()["data"][0]["transaction_count"] == 5
    assert project.json()["data"][0]["transaction_count"] == 2
    assert authenticated_api["billing_aggregate"].calls[-2][0] == "getAggregateByOrg"
    assert authenticated_api["billing_aggregate"].calls[-1][0] == "getAggregateByProjects"


@pytest.mark.asyncio
async def test_billing_source_lifecycle_contract(api_client, authenticated_api) -> None:
    created = await api_client.post(
        "/v1/billing/sources",
        headers=AUTH,
        json={"name": "Billing User", "email": "billing@example.com", "phone": "+10000000000", "address": ADDRESS, "provider": "stripe"},
    )
    detail = await api_client.get("/v1/billing/sources", headers=AUTH)
    updated = await api_client.put(
        "/v1/billing/sources",
        headers=AUTH,
        json={"new_address": ADDRESS, "new_email": "new@example.com", "new_phone": "+10000000001"},
    )
    setup = await api_client.post("/v1/billing/sources/setup_intents", headers=AUTH)
    methods = await api_client.get("/v1/billing/sources/payment_methods", headers=AUTH)
    method_detail = await api_client.get("/v1/billing/sources/payment_methods/pm_123", headers=AUTH)
    required_actions = await api_client.get("/v1/billing/sources/setup_intents/required_actions", headers=AUTH)
    delete_method = await api_client.delete("/v1/billing/sources/payment_method/pm_123", headers=AUTH)
    cancel_setup = await api_client.delete("/v1/billing/sources/setup_intents/seti_123", headers=AUTH)

    assert created.status_code == 200
    assert created.json()["data"]["source_type"] == "stripe"
    assert detail.status_code == 200
    assert detail.json()["data"]["provider_id"] == "cus_123"
    assert updated.status_code == 200
    assert setup.json()["client_secret"] == "seti_secret"
    assert methods.json()[0]["id"] == "pm_123"
    assert method_detail.json()["id"] == "pm_123"
    assert required_actions.json()[0]["status"] == "requires_action"
    assert delete_method.status_code == 200
    assert cancel_setup.status_code == 200


@pytest.mark.asyncio
async def test_billing_credit_invoice_and_transaction_contract(api_client, authenticated_api) -> None:
    credits = await api_client.get("/v1/billing/credits/available", headers=AUTH)
    credit_transactions = await api_client.get(
        "/v1/billing/credits/transactions",
        headers=AUTH,
        params={"limit": 7, "offset": 3},
    )
    invoices = await api_client.get(
        "/v1/billing/invoices",
        headers=AUTH,
        params={"limit": 5, "offset": 2, "paid": False},
    )
    invoice = await api_client.get(f"/v1/billing/invoices/{INVOICE_UUID}", headers=AUTH)
    payment = await api_client.post(f"/v1/billing/invoices/{INVOICE_UUID}/pay", headers=AUTH)
    transaction_list = await api_client.get(
        "/v1/billing/transactions",
        headers=AUTH,
        params={"project_uuids": PROJECT_UUID, "limit": 9, "offset": 4},
    )
    transaction = await api_client.get(f"/v1/billing/transactions/{TRANSACTION_UUID}", headers=AUTH)

    assert credits.status_code == 200
    assert credits.json()["data"]["amount"] == "42.00"
    assert credit_transactions.status_code == 200
    assert credit_transactions.json()["limit"] == 7
    assert invoices.status_code == 200
    assert invoices.json()["limit"] == 5
    assert invoice.json()["data"]["line_items"][0]["project_uuid"] == PROJECT_UUID
    assert payment.json()["data"]["hosted_invoice_url"] == "https://billing.example/pay"
    assert transaction_list.status_code == 200
    assert transaction_list.json()["limit"] == 9
    assert transaction.json()["data"]["transaction_uid"] == TRANSACTION_UUID


@pytest.mark.asyncio
async def test_billing_webhook_rejects_invalid_signature_without_auth(api_client, authenticated_api) -> None:
    response = await api_client.post(
        "/v1/billing/webhook/stripe",
        headers={"stripe-signature": "invalid"},
        content=b"{}",
    )

    assert response.status_code == 400
