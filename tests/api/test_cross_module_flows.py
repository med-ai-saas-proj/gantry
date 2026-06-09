from __future__ import annotations

import json

import httpx
import pytest
import respx

from tests.api.fakes import (
    BILLING_SOURCE_UUID,
    CONVERSATION_UUID,
    FILE_UUID,
    INVOICE_UUID,
    PROJECT_UUID,
    TRANSACTION_UUID,
)
from tests.helpers.http import assert_paginated

pytestmark = pytest.mark.api

AUTH = {"Authorization": "Bearer test-token"}
ADMIN_AUTH = {"Authorization": "Bearer admin-token"}
API_KEY_AUTH = {"X-Api-Key": "sk_test"}
SERVICE_AUTH = {"Authorization": "Bearer test-token", "X-Api-Key": "sk_test"}
LOG_START = "2026-01-01T00:00:00Z"
LOG_END = "2026-01-01T01:00:00Z"


def _upstream_response() -> httpx.Response:
    return httpx.Response(
        202,
        json={"accepted": True},
        headers={"Content-Type": "application/json"},
    )


@pytest.mark.asyncio
async def test_admin_seeded_project_can_be_used_by_user_project_and_api_key_routes(
    api_client,
    authenticated_api,
) -> None:
    created_project = await api_client.post(
        "/v1/admin/projects",
        headers=ADMIN_AUTH,
        params={"org_id": "org-1"},
        json={"name": "Seeded Project", "description": "created by admin"},
    )
    assert created_project.status_code == 201
    assert created_project.json()["project_uuid"] == PROJECT_UUID

    project_detail = await api_client.get(f"/v1/projects/{PROJECT_UUID}", headers=AUTH)
    assert project_detail.status_code == 200
    assert project_detail.json()["project_uuid"] == PROJECT_UUID

    created_key = await api_client.post(
        "/v1/api-keys",
        headers=AUTH,
        params={"project_id": PROJECT_UUID},
        json={"name": "User Key", "description": "desc", "permissions": ["chat.read"]},
    )
    assert created_key.status_code == 201
    assert created_key.json()["project_uuid"] == PROJECT_UUID

    key_detail = await api_client.get("/v1/api-keys/api-key-1", headers=AUTH)
    assert key_detail.status_code == 200
    assert key_detail.json()["api_key_uuid"] == "api-key-1"

    assert authenticated_api["admin"].calls[0][0] == "createProject"
    assert authenticated_api["api_key"].calls[:3] == [
        ("createApiKey", {
            "actor_user_id": "user-1",
            "project_uuid": PROJECT_UUID,
            "name": "User Key",
            "description": "desc",
            "permissions": ["chat.read"],
        }),
        ("getApiKeyProjectUuid", "api-key-1"),
        ("getApiKey", "api-key-1"),
    ]


@pytest.mark.asyncio
async def test_org_project_member_permission_flow_keeps_actor_and_target_context(
    api_client,
    authenticated_api,
) -> None:
    org_perms = await api_client.get(
        "/v1/organizations/org-1/users/user-2/permissions",
        headers=AUTH,
    )
    assert org_perms.status_code == 200
    assert org_perms.json()["permissions"] == ["organization.settings.read"]
    assert authenticated_api["org"].calls[-2] == (
        "ensureCanReadUserPermissions",
        {"org_id": "org-1", "actor_user_id": "user-1", "target_user_id": "user-2"},
    )

    org_update = await api_client.put(
        "/v1/organizations/org-1/users/user-2/permissions",
        headers=AUTH,
        json={"permissions": ["organization.settings.read"]},
    )
    assert org_update.status_code == 200
    assert authenticated_api["org"].calls[-1] == (
        "updateUserPermissions",
        {
            "org_id": "org-1",
            "actor_user_id": "user-1",
            "user_id": "user-2",
            "permissions": ["organization.settings.read"],
        },
    )

    add_user = await api_client.post(
        f"/v1/projects/{PROJECT_UUID}/users",
        headers=AUTH,
        json={"user_id": "user-2"},
    )
    assert add_user.status_code == 200

    project_perms = await api_client.get(
        f"/v1/projects/{PROJECT_UUID}/users/user-2/permissions",
        headers=AUTH,
    )
    assert project_perms.status_code == 200
    assert authenticated_api["project"].calls[-1] == (
        "getUserPermissions",
        {"project_uuid": PROJECT_UUID, "target_user_id": "user-2"},
    )

    project_update = await api_client.put(
        f"/v1/projects/{PROJECT_UUID}/users/user-2/permissions",
        headers=AUTH,
        json={"permissions": ["project.settings.read"]},
    )
    assert project_update.status_code == 200
    assert authenticated_api["project"].calls[-1] == (
        "updateUserPermissions",
        {
            "project_uuid": PROJECT_UUID,
            "actor_user_id": "user-1",
            "target_user_id": "user-2",
            "permissions": ["project.settings.read"],
        },
    )

    remove_project_user = await api_client.delete(
        f"/v1/projects/{PROJECT_UUID}/users/user-2",
        headers=AUTH,
    )
    assert remove_project_user.status_code == 200

    remove_org_user = await api_client.delete(
        "/v1/organizations/org-1/users/user-2",
        headers=AUTH,
    )
    assert remove_org_user.status_code == 200


@pytest.mark.asyncio
async def test_admin_permission_change_response_can_drive_user_project_read(
    api_client,
    authenticated_api,
) -> None:
    permission_update = await api_client.put(
        "/v1/admin/users/user-1/permissions",
        headers=ADMIN_AUTH,
        json={
            "organization_permissions": ["organization.settings.read"],
            "project_permissions": [
                {"project_uuid": PROJECT_UUID, "permissions": ["project.settings.read"]}
            ],
        },
    )
    assert permission_update.status_code == 200
    project_permissions = permission_update.json()["permissions"]["project_permissions"]
    assert project_permissions == [
        {
            "project_uuid": PROJECT_UUID,
            "permissions": ["project.settings.read"],
            "effective_permissions": ["project.settings.read"],
        }
    ]

    listed = await api_client.get("/v1/projects", headers=AUTH)
    assert listed.status_code == 200
    assert_paginated(listed.json())

    settings = await api_client.get(f"/v1/projects/{PROJECT_UUID}/settings", headers=AUTH)
    assert settings.status_code == 200
    assert settings.json()["rate_limit"] == 120


@pytest.mark.asyncio
async def test_admin_scoped_permission_updates_keep_org_and_project_boundaries(
    api_client,
    authenticated_api,
) -> None:
    org_update = await api_client.put(
        "/v1/admin/organizations/org-1/users/user-2/permissions",
        headers=ADMIN_AUTH,
        json={"permissions": ["organization.settings.write"]},
    )
    project_update = await api_client.put(
        f"/v1/admin/projects/{PROJECT_UUID}/users/user-2/permissions",
        headers=ADMIN_AUTH,
        json={"permissions": ["project.settings.write"]},
    )

    assert org_update.status_code == 200
    assert org_update.json()["permissions"]["organization_permissions"] == [
        "organization.settings.write"
    ]
    assert org_update.json()["permissions"]["project_permissions"][0] == {
        "project_uuid": PROJECT_UUID,
        "permissions": ["project.settings.read"],
        "effective_permissions": ["project.settings.read"],
    }
    assert project_update.status_code == 200
    assert project_update.json()["permissions"]["organization_permissions"] == [
        "organization.settings.read"
    ]
    assert project_update.json()["permissions"]["project_permissions"][0] == {
        "project_uuid": PROJECT_UUID,
        "permissions": ["project.settings.write"],
        "effective_permissions": ["project.settings.write"],
    }
    assert authenticated_api["admin"].calls[-2:] == [
        (
            "setUserOrganizationPermissions",
            {
                "user_id": "user-2",
                "org_id": "org-1",
                "permissions": ["organization.settings.write"],
            },
        ),
        (
            "setUserProjectPermissions",
            {
                "user_id": "user-2",
                "project_id": PROJECT_UUID,
                "permissions": ["project.settings.write"],
            },
        ),
    ]

    org_permission_read = await api_client.get(
        "/v1/organizations/org-1/users/user-2/permissions",
        headers=AUTH,
    )
    project_permission_read = await api_client.get(
        f"/v1/projects/{PROJECT_UUID}/users/user-2/permissions",
        headers=AUTH,
    )

    assert org_permission_read.status_code == 200
    assert project_permission_read.status_code == 200
    assert authenticated_api["org"].calls[-2][0] == "ensureCanReadUserPermissions"
    assert authenticated_api["project"].calls[-1] == (
        "getUserPermissions",
        {"project_uuid": PROJECT_UUID, "target_user_id": "user-2"},
    )


@pytest.mark.asyncio
async def test_admin_project_settings_and_archive_flow_stays_readable_to_user(
    api_client,
    authenticated_api,
) -> None:
    project = await api_client.post(
        "/v1/admin/projects",
        headers=ADMIN_AUTH,
        params={"org_id": "org-1"},
        json={"name": "Cross Module Project", "description": "seeded"},
    )
    settings = await api_client.patch(
        f"/v1/admin/projects/{PROJECT_UUID}/settings",
        headers=ADMIN_AUTH,
        json={
            "rate_limit": 333,
            "spending_limit": 9999,
            "extra": {"mode": "cross-module"},
        },
    )
    archived = await api_client.post(
        f"/v1/admin/projects/{PROJECT_UUID}/archive",
        headers=ADMIN_AUTH,
    )
    unarchived = await api_client.post(
        f"/v1/admin/projects/{PROJECT_UUID}/unarchive",
        headers=ADMIN_AUTH,
    )
    user_project = await api_client.get(
        f"/v1/projects/{PROJECT_UUID}",
        headers=AUTH,
    )
    user_settings = await api_client.get(
        f"/v1/projects/{PROJECT_UUID}/settings",
        headers=AUTH,
    )

    assert project.status_code == 201
    assert settings.status_code == 200
    assert settings.json()["extra"] == {"mode": "cross-module"}
    assert archived.json() == {"id": PROJECT_UUID, "archived": True}
    assert unarchived.json() == {"id": PROJECT_UUID, "archived": False}
    assert user_project.status_code == 200
    assert user_settings.status_code == 200
    assert authenticated_api["admin"].calls[:4] == [
        (
            "createProject",
            {
                "org_id": "org-1",
                "input_data": authenticated_api["admin"].calls[0][1][
                    "input_data"
                ],
            },
        ),
        (
            "updateProjectSettings",
            {
                "project_id": PROJECT_UUID,
                "input_data": authenticated_api["admin"].calls[1][1][
                    "input_data"
                ],
            },
        ),
        ("archiveProject", PROJECT_UUID),
        ("unarchiveProject", PROJECT_UUID),
    ]
    assert any(
        call[0] == "getProject" and call[1]["project_uuid"] == PROJECT_UUID
        for call in authenticated_api["project"].calls
    )
    assert ("getProjectSettings", PROJECT_UUID) in (
        authenticated_api["project"].calls
    )


@pytest.mark.asyncio
async def test_admin_api_key_can_drive_service_conversation_file_and_rag_paths(
    api_client,
    service_client,
    authenticated_api,
    authenticated_service_api,
) -> None:
    created_key = await api_client.post(
        "/v1/admin/api-keys",
        headers=ADMIN_AUTH,
        params={"project_id": PROJECT_UUID},
        json={
            "name": "Service Key",
            "description": "service contract",
            "permissions": ["chat.read"],
        },
    )
    conversation = await service_client.post(
        "/v1/conversations/sequence/",
        headers=API_KEY_AUTH,
        json={"extra_metadata": {"source": "admin-api-key"}},
    )
    uploaded_file = await service_client.post(
        "/v1/file-storage/service/",
        headers=SERVICE_AUTH,
        files={"file": ("report.txt", b"hello", "text/plain")},
    )
    rag_task = await service_client.post(
        "/v1/rag/service/files",
        headers=SERVICE_AUTH,
        json={"file_uid": FILE_UUID, "chunk_size": 100, "chunk_overlap": 10},
    )
    rag_query = await service_client.post(
        "/v1/rag/service/query/text",
        headers=SERVICE_AUTH,
        json={"query_text": "hello", "top_k": 3},
    )

    assert created_key.status_code == 201
    assert created_key.json()["key"].startswith("sk_")
    assert conversation.status_code == 201
    assert conversation.json()["conversation_uid"] == CONVERSATION_UUID
    assert uploaded_file.status_code == 201
    assert uploaded_file.json()["file_id"] == FILE_UUID
    assert rag_task.status_code == 201
    assert rag_task.json() == "task-1"
    assert rag_query.status_code == 200
    assert rag_query.json()[0]["file_info"]["id"] == FILE_UUID
    assert authenticated_api["admin"].calls[-1][0] == "createApiKey"
    assert authenticated_service_api["sequence_conversation"].calls[0] == (
        "createConversation",
        {
            "project_id": 20,
            "extra_metadata": {"source": "admin-api-key"},
            "msg_count": 0,
        },
    )
    upload_call = authenticated_service_api["file_storage"].calls[0]
    assert upload_call[0] == "uploadFile"
    assert upload_call[1][0] == "report.txt"
    assert upload_call[1][2:] == (5, "text/plain", 20, "txt")
    assert authenticated_service_api["rag"].calls[-2][0] == "addFile"
    assert authenticated_service_api["rag"].calls[-1][0] == "querySimilarByText"


@pytest.mark.asyncio
async def test_internal_usage_capture_is_visible_to_management_billing_and_logs(
    internal_client,
    api_client,
    authenticated_internal_api,
    authenticated_api,
) -> None:
    posted = await internal_client.post(
        "/billing/",
        headers={"X-Api-Key": "sk_test", "idempotency-key": "idem-cross"},
        json={
            "api_key_uuid": "77777777-7777-7777-7777-777777777777",
            "amount": {"value": 1234, "scale": 2},
            "details": {"route": "chat", "tokens": 9},
            "capture": False,
        },
    )
    captured = await internal_client.post(
        f"/billing/{TRANSACTION_UUID}/capture",
        headers={"X-Api-Key": "sk_test"},
        json={"real_amount": {"value": 1200, "scale": 2}},
    )
    user_transactions = await api_client.get(
        "/v1/billing/transactions",
        headers=AUTH,
        params={"project_uuids": PROJECT_UUID, "limit": 5, "offset": 0},
    )
    project_aggregate = await api_client.get(
        "/v1/billing/aggregates/projects",
        headers=AUTH,
        params={
            "period_start": LOG_START,
            "period_end": "2026-01-31T00:00:00Z",
            "period": "daily",
            "project_uuids": PROJECT_UUID,
        },
    )
    logs = await api_client.post(
        "/v1/logging/",
        headers=AUTH,
        json={
            "start": LOG_START,
            "end": LOG_END,
            "limit": 10,
            "direction": "backward",
            "level": "info",
            "keyword": "chat",
            "filters": {"project_uuid": PROJECT_UUID},
            "custom_query": None,
        },
    )

    assert posted.status_code == 200
    assert posted.json() == TRANSACTION_UUID
    assert captured.status_code == 200
    assert captured.json() is True
    assert user_transactions.status_code == 200
    assert user_transactions.json()["data"][0]["transaction_uid"] == TRANSACTION_UUID
    assert project_aggregate.status_code == 200
    assert project_aggregate.json()["data"][0]["transaction_count"] == 2
    assert logs.status_code == 200
    assert logs.json()[0]["message"] == "ok"
    post_call, capture_call = authenticated_internal_api[
        "billing_transaction"
    ].calls[:2]
    assert post_call[0] == "post"
    assert str(post_call[1]["req"].api_key_uuid) == (
        "77777777-7777-7777-7777-777777777777"
    )
    assert post_call[1]["idempotency_key"] == "idem-cross"
    assert post_call[1]["req"].details == {"route": "chat", "tokens": 9}
    assert post_call[1]["req"].capture is False
    assert capture_call[0] == "capture"
    assert str(capture_call[1]["transaction_uid"]) == TRANSACTION_UUID
    assert authenticated_api["billing_transaction"].calls[-1][0] == "getTransactions"
    assert authenticated_api["billing_aggregate"].calls[-1][0] == "getAggregateByProjects"
    assert authenticated_api["logging"].calls[-1][1][0] == "org-1"


@pytest.mark.asyncio
async def test_gateway_proxy_preserves_api_key_context_after_admin_catalog_lookup(
    api_client,
    gateway_client,
    authenticated_api,
    authenticated_gateway_api,
) -> None:
    permission_catalog = await api_client.get(
        "/v1/admin/api-keys/permissions",
        headers=ADMIN_AUTH,
    )

    with respx.mock(assert_all_called=True) as router:
        upstream = router.post(
            "https://upstream.example/base/v1/messages"
        ).mock(return_value=_upstream_response())
        response = await gateway_client.post(
            "/chat/v1/messages",
            headers={"X-Api-Key": "sk_test", "X-Client": "cross-module"},
            json={"message": "hello"},
        )

    assert permission_catalog.status_code == 200
    assert permission_catalog.json()["results"][0]["id"] == "chat.read"
    assert response.status_code == 202
    assert response.json() == {"accepted": True}
    request = upstream.calls.last.request
    assert request.headers["X-Client"] == "cross-module"
    assert request.headers["X-Organization-UUID"] == "org-1"
    assert request.headers["X-Project-UUID"] == PROJECT_UUID
    assert request.headers["X-API-Key-UUID"] == "api-key-1"
    assert "conversation.read" in json.loads(request.headers["X-Permissions"])
    assert authenticated_api["admin"].calls == []
    assert authenticated_gateway_api["gateway"].calls[0] == ("getDestination", "chat")
    assert authenticated_gateway_api["gateway"].calls[1][0] == "checkPermission"


@pytest.mark.asyncio
async def test_user_org_admin_workbench_flow_covers_invites_delete_and_billing(
    api_client,
    authenticated_api,
) -> None:
    org_detail = await api_client.get("/v1/organizations/org-1", headers=AUTH)
    org_update = await api_client.patch(
        "/v1/organizations/org-1",
        headers=AUTH,
        json={"name": "Org 1 renamed"},
    )
    org_users = await api_client.get(
        "/v1/organizations/org-1/users",
        headers=AUTH,
        params={"limit": 10, "offset": 0, "q": "alice"},
    )
    invitations = await api_client.get(
        "/v1/organizations/org-1/invitations",
        headers=AUTH,
    )
    invite = await api_client.post(
        "/v1/organizations/org-1/invitations",
        headers=AUTH,
        json={"email": "new-user@example.com"},
    )
    invitation_detail = await api_client.get(
        "/v1/organizations/org-1/invitations/inv-1",
        headers=AUTH,
    )
    resend = await api_client.post(
        "/v1/organizations/org-1/invitations/inv-1/resend",
        headers=AUTH,
    )
    delete_invitation = await api_client.delete(
        "/v1/organizations/org-1/invitations/inv-1",
        headers=AUTH,
    )
    delete_request = await api_client.delete("/v1/organizations/org-1", headers=AUTH)
    cancel_delete = await api_client.post(
        "/v1/organizations/org-1/deletion/cancel",
        headers=AUTH,
    )

    source_payload = {
        "name": "Billing Contact",
        "email": "billing@example.com",
        "phone": "+10000000000",
        "address": {
            "line1": "1 Main",
            "line2": "Suite 1",
            "city": "HCM",
            "state": "HCM",
            "postal_code": "70000",
            "country": "VN",
        },
        "provider": "stripe",
    }
    billing_source = await api_client.post(
        "/v1/billing/sources",
        headers=AUTH,
        json=source_payload,
    )
    billing_source_detail = await api_client.get("/v1/billing/sources", headers=AUTH)
    billing_source_update = await api_client.put(
        "/v1/billing/sources",
        headers=AUTH,
        json={
            "new_address": source_payload["address"],
            "new_email": "billing-updated@example.com",
            "new_phone": "+19999999999",
        },
    )
    setup_intent = await api_client.post(
        "/v1/billing/sources/setup_intents",
        headers=AUTH,
    )
    payment_methods = await api_client.get(
        "/v1/billing/sources/payment_methods",
        headers=AUTH,
    )
    payment_method = await api_client.get(
        "/v1/billing/sources/payment_methods/pm_123",
        headers=AUTH,
    )
    required_actions = await api_client.get(
        "/v1/billing/sources/setup_intents/required_actions",
        headers=AUTH,
    )
    cancel_setup = await api_client.delete(
        "/v1/billing/sources/setup_intents/seti_123",
        headers=AUTH,
    )
    delete_payment_method = await api_client.delete(
        "/v1/billing/sources/payment_method/pm_123",
        headers=AUTH,
    )
    available_credits = await api_client.get(
        "/v1/billing/credits/available",
        headers=AUTH,
    )
    credit_transactions = await api_client.get(
        "/v1/billing/credits/transactions",
        headers=AUTH,
    )
    invoices = await api_client.get("/v1/billing/invoices", headers=AUTH)
    invoice_detail = await api_client.get(
        f"/v1/billing/invoices/{INVOICE_UUID}",
        headers=AUTH,
    )
    invoice_pay = await api_client.post(
        f"/v1/billing/invoices/{INVOICE_UUID}/pay",
        headers=AUTH,
    )

    assert org_detail.status_code == 200
    assert org_update.status_code == 200
    assert org_update.json()["name"] == "Org 1 renamed"
    assert org_users.status_code == 200
    assert invitations.status_code == 200
    assert invite.status_code == 200
    assert invitation_detail.status_code == 200
    assert invitation_detail.json()["id"] == "inv-1"
    assert resend.status_code == 200
    assert delete_invitation.status_code == 200
    assert delete_request.status_code == 202
    assert cancel_delete.status_code == 200
    assert cancel_delete.json() == {"id": "org-1", "cancelled": True}

    assert billing_source.status_code == 200
    assert billing_source.json()["data"]["billing_source_uid"] == BILLING_SOURCE_UUID
    assert billing_source_detail.status_code == 200
    assert billing_source_update.status_code == 200
    assert setup_intent.status_code == 200
    assert setup_intent.json()["client_secret"] == "seti_secret"
    assert payment_methods.status_code == 200
    assert payment_methods.json()[0]["id"] == "pm_123"
    assert payment_method.status_code == 200
    assert required_actions.status_code == 200
    assert cancel_setup.status_code == 200
    assert delete_payment_method.status_code == 200
    assert available_credits.status_code == 200
    assert available_credits.json()["data"]["amount"] == "42.00"
    assert credit_transactions.status_code == 200
    assert invoices.status_code == 200
    assert invoice_detail.status_code == 200
    assert invoice_pay.status_code == 200
    assert invoice_pay.json()["data"]["hosted_invoice_url"] == "https://billing.example/pay"

    assert authenticated_api["org"].calls[:10] == [
        ("getOrgInfo", "org-1"),
        (
            "updateOrgInfo",
            {"org_id": "org-1", "actor_user_id": "user-1", "name": "Org 1 renamed"},
        ),
        ("getUsers", {"org_id": "org-1", "offset": 0, "limit": 10, "q": "alice"}),
        ("getInvitations", "org-1"),
        ("createInvitation", {"org_id": "org-1", "email": "new-user@example.com"}),
        ("getInvitation", {"org_id": "org-1", "invitation_id": "inv-1"}),
        ("resendInvitation", {"org_id": "org-1", "invitation_id": "inv-1"}),
        ("deleteInvitation", {"org_id": "org-1", "invitation_id": "inv-1"}),
        ("requestDeleteOrg", "org-1"),
        ("cancelDeleteOrg", "org-1"),
    ]
    assert authenticated_api["billing_source"].calls[0][0] == "createBillingSource"
    assert authenticated_api["invoice"].calls[-1][0] == "getInvoiceByIdPaymentLinkInProvider"


@pytest.mark.asyncio
async def test_admin_backoffice_flow_spans_users_api_keys_and_billing_admin_views(
    api_client,
    authenticated_api,
) -> None:
    users = await api_client.get("/v1/admin/users", headers=ADMIN_AUTH, params={"q": "alice"})
    profile = await api_client.get("/v1/admin/users/user-1/profile", headers=ADMIN_AUTH)
    organizations = await api_client.get(
        "/v1/admin/users/user-1/organizations",
        headers=ADMIN_AUTH,
    )
    permissions = await api_client.get(
        "/v1/admin/users/user-1/permissions",
        headers=ADMIN_AUTH,
    )
    reset_permissions = await api_client.delete(
        "/v1/admin/users/user-1/permissions",
        headers=ADMIN_AUTH,
    )
    orgs = await api_client.get("/v1/admin/organizations", headers=ADMIN_AUTH)
    org_detail = await api_client.get("/v1/admin/organizations/org-1", headers=ADMIN_AUTH)
    org_settings = await api_client.get(
        "/v1/admin/organizations/org-1/settings",
        headers=ADMIN_AUTH,
    )
    org_users = await api_client.get(
        "/v1/admin/organizations/org-1/users",
        headers=ADMIN_AUTH,
    )
    projects = await api_client.get(
        "/v1/admin/projects",
        headers=ADMIN_AUTH,
        params={"org_id": "org-1"},
    )
    project_users = await api_client.get(
        f"/v1/admin/projects/{PROJECT_UUID}/users",
        headers=ADMIN_AUTH,
    )
    api_keys = await api_client.get(
        "/v1/admin/api-keys",
        headers=ADMIN_AUTH,
        params={"project_id": PROJECT_UUID, "disabled": "true"},
    )
    api_key_detail = await api_client.get(
        "/v1/admin/api-keys/api-key-1",
        headers=ADMIN_AUTH,
        params={"disabled": "true"},
    )
    api_key_update = await api_client.put(
        "/v1/admin/api-keys/api-key-1",
        headers=ADMIN_AUTH,
        json={
            "name": "disabled key",
            "description": "admin update",
            "permissions": ["chat.read"],
            "disabled": True,
        },
    )
    credit_add = await api_client.post(
        "/v1/billing/admin/credits",
        headers=ADMIN_AUTH,
        json={
            "org_id": "org-1",
            "amount": {"value": 500, "scale": 2},
            "description": "promo",
        },
    )
    admin_credits = await api_client.get(
        "/v1/billing/admin/credits/org-1/available",
        headers=ADMIN_AUTH,
    )
    admin_credit_transactions = await api_client.get(
        "/v1/billing/admin/credits/org-1/transactions",
        headers=ADMIN_AUTH,
    )
    admin_transactions = await api_client.get(
        "/v1/billing/admin/transactions",
        headers=ADMIN_AUTH,
        params={"project_uuids": PROJECT_UUID},
    )
    admin_transaction_detail = await api_client.get(
        f"/v1/billing/admin/transactions/{TRANSACTION_UUID}",
        headers=ADMIN_AUTH,
    )
    admin_project_aggregate = await api_client.get(
        "/v1/billing/admin/aggregates/projects",
        headers=ADMIN_AUTH,
        params={
            "period_start": LOG_START,
            "period_end": "2026-01-31T00:00:00Z",
            "period": "daily",
            "project_uuids": PROJECT_UUID,
        },
    )
    admin_org_aggregate = await api_client.get(
        "/v1/billing/admin/aggregates/organizations",
        headers=ADMIN_AUTH,
        params={
            "period_start": LOG_START,
            "period_end": "2026-01-31T00:00:00Z",
            "period": "daily",
            "org_id": "org-1",
        },
    )
    admin_invoices = await api_client.get(
        "/v1/billing/admin/invoices",
        headers=ADMIN_AUTH,
        params={"org_ids": "org-1"},
    )
    admin_invoice_detail = await api_client.get(
        f"/v1/billing/admin/invoices/{INVOICE_UUID}",
        headers=ADMIN_AUTH,
    )
    mark_paid = await api_client.put(
        f"/v1/billing/admin/invoices/{INVOICE_UUID}/mark_paid",
        headers=ADMIN_AUTH,
    )
    refund = await api_client.post(
        f"/v1/billing/admin/invoices/{INVOICE_UUID}/refund",
        headers=ADMIN_AUTH,
    )

    for response in [
        users,
        profile,
        organizations,
        permissions,
        reset_permissions,
        orgs,
        org_detail,
        org_settings,
        org_users,
        projects,
        project_users,
        api_keys,
        api_key_detail,
        api_key_update,
        credit_add,
        admin_credits,
        admin_credit_transactions,
        admin_transactions,
        admin_transaction_detail,
        admin_project_aggregate,
        admin_org_aggregate,
        admin_invoices,
        admin_invoice_detail,
        mark_paid,
        refund,
    ]:
        assert response.status_code < 500, response.text

    assert users.status_code == 200
    assert profile.json()["user_id"] == "user-1"
    assert organizations.json()[0]["org_id"] == "org-1"
    assert permissions.json()["organization_permissions"] == [
        "organization.settings.read"
    ]
    assert reset_permissions.json()["permissions"]["project_permissions"] == []
    assert api_keys.json()["results"][0]["disabled"] is True
    assert api_key_detail.json()["disabled"] is True
    assert api_key_update.json()["disabled"] is True
    assert credit_add.json()["data"]["amount"] == "47.00"
    assert admin_transactions.json()["data"][0]["transaction_uid"] == TRANSACTION_UUID
    assert admin_project_aggregate.json()["data"][0]["transaction_count"] == 3
    assert admin_org_aggregate.json()["data"][0]["transaction_count"] == 5
    assert admin_invoices.json()["data"][0]["invoice_uid"] == INVOICE_UUID
    assert admin_invoice_detail.json()["data"]["line_items"][0]["description"] == "usage"

    assert ("listApiKeys", {"project_id": PROJECT_UUID, "disabled": True}) in (
        authenticated_api["admin"].calls
    )
    assert (
        "getApiKey",
        {"api_key_uuid": "api-key-1", "disabled": True},
    ) in authenticated_api["admin"].calls
    assert authenticated_api["credit"].calls[0][0] == "addCredits"
    assert authenticated_api["billing_transaction"].calls[0][0] == "getTransactionsForAdmin"
    assert authenticated_api["billing_aggregate"].calls[-2][0] == (
        "getAggregateByProjectsForAdmin"
    )
