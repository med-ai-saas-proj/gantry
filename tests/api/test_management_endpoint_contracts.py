from __future__ import annotations

import pytest

from tests.helpers.http import assert_paginated

pytestmark = pytest.mark.api

AUTH = {"Authorization": "Bearer test-token"}


@pytest.mark.asyncio
async def test_all_management_operations_match_committed_snapshot(
    management_openapi: dict, repo_root
) -> None:
    operations = []
    for path, methods in sorted(management_openapi["paths"].items()):
        for method in sorted(methods):
            if method in {"get", "post", "put", "patch", "delete"}:
                operations.append(f"{method.upper()}\t{path}")

    expected = (repo_root / "tests" / "snapshots" / "management_operations.tsv").read_text()
    assert "\n".join(operations) + "\n" == expected


@pytest.mark.asyncio
async def test_organization_metadata_settings_users_and_permissions_contract(
    api_client, authenticated_api
) -> None:
    info = await api_client.get("/v1/organizations/org-1", headers=AUTH)
    assert info.status_code == 200
    assert info.json()["org_id"] == "org-1"

    updated = await api_client.patch(
        "/v1/organizations/org-1",
        headers=AUTH,
        json={"name": "Updated Org"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Org"

    settings = await api_client.patch(
        "/v1/organizations/org-1/settings",
        headers=AUTH,
        json={"rate_limit": 250, "spending_limit": 1000, "extra": {"tier": "pro"}},
    )
    assert settings.status_code == 200
    assert settings.json() == {"rate_limit": 250, "spending_limit": 1000, "extra": {"tier": "pro"}}

    users = await api_client.get(
        "/v1/organizations/org-1/users",
        headers=AUTH,
        params={"limit": 5, "offset": 2, "q": "alice"},
    )
    assert users.status_code == 200
    assert_paginated(users.json())
    assert authenticated_api["org"].calls[-1] == (
        "getUsers",
        {"org_id": "org-1", "offset": 2, "limit": 5, "q": "alice"},
    )

    perms = await api_client.put(
        "/v1/organizations/org-1/users/user-2/permissions",
        headers=AUTH,
        json={"permissions": ["organization.settings.read"]},
    )
    assert perms.status_code == 200
    assert perms.json()["permissions"] == ["organization.settings.read"]


@pytest.mark.asyncio
async def test_organization_invitation_and_delete_contract(api_client, authenticated_api) -> None:
    create_invite = await api_client.post(
        "/v1/organizations/org-1/invitations",
        headers=AUTH,
        json={"email": "new-user@example.com"},
    )
    assert create_invite.status_code == 200

    invitations = await api_client.get("/v1/organizations/org-1/invitations", headers=AUTH)
    assert invitations.status_code == 200
    assert invitations.json()["results"][0]["email"] == "a@example.com"

    invitation = await api_client.get("/v1/organizations/org-1/invitations/inv-1", headers=AUTH)
    assert invitation.status_code == 200
    assert invitation.json()["id"] == "inv-1"

    resend = await api_client.post("/v1/organizations/org-1/invitations/inv-1/resend", headers=AUTH)
    assert resend.status_code == 200

    delete_invite = await api_client.delete("/v1/organizations/org-1/invitations/inv-1", headers=AUTH)
    assert delete_invite.status_code == 200

    delete_org = await api_client.delete("/v1/organizations/org-1", headers=AUTH)
    assert delete_org.status_code == 202
    assert delete_org.json()["id"] == "org-1"

    cancel_delete = await api_client.post("/v1/organizations/org-1/deletion/cancel", headers=AUTH)
    assert cancel_delete.status_code == 200
    assert cancel_delete.json() == {"id": "org-1", "cancelled": True}


@pytest.mark.asyncio
async def test_project_lifecycle_settings_members_permissions_and_state_contract(
    api_client, authenticated_api
) -> None:
    listed = await api_client.get("/v1/projects", headers=AUTH)
    assert listed.status_code == 200
    assert_paginated(listed.json())

    org_listed = await api_client.get("/v1/projects", headers=AUTH, params={"organization": "org-1"})
    assert org_listed.status_code == 200

    created = await api_client.post(
        "/v1/projects",
        headers=AUTH,
        params={"organization": "org-1"},
        json={"name": "Project 1", "description": "desc"},
    )
    assert created.status_code == 201
    assert created.json()["project_uuid"] == "11111111-1111-1111-1111-111111111111"

    updated = await api_client.put(
        "/v1/projects/11111111-1111-1111-1111-111111111111",
        headers=AUTH,
        json={"name": "Project 2", "description": "updated"},
    )
    assert updated.status_code == 200

    settings = await api_client.patch(
        "/v1/projects/11111111-1111-1111-1111-111111111111/settings",
        headers=AUTH,
        json={"rate_limit": 300, "spending_limit": 999, "extra": {"mode": "strict"}},
    )
    assert settings.status_code == 200
    assert settings.json()["rate_limit"] == 300

    users = await api_client.get("/v1/projects/11111111-1111-1111-1111-111111111111/users", headers=AUTH, params={"limit": 3, "offset": 1, "q": "bob"})
    assert users.status_code == 200
    assert_paginated(users.json())

    add_user = await api_client.post("/v1/projects/11111111-1111-1111-1111-111111111111/users", headers=AUTH, json={"user_id": "user-2"})
    assert add_user.status_code == 200

    permissions = await api_client.put(
        "/v1/projects/11111111-1111-1111-1111-111111111111/users/user-2/permissions",
        headers=AUTH,
        json={"permissions": ["project.settings.read"]},
    )
    assert permissions.status_code == 200
    assert permissions.json()["permissions"] == ["project.settings.read"]

    archive = await api_client.post("/v1/projects/11111111-1111-1111-1111-111111111111/archive", headers=AUTH)
    assert archive.status_code == 200
    assert archive.json()["archived"] is True

    unarchive = await api_client.post("/v1/projects/11111111-1111-1111-1111-111111111111/unarchive", headers=AUTH)
    assert unarchive.status_code == 200
    assert unarchive.json()["archived"] is False


@pytest.mark.asyncio
async def test_api_key_lifecycle_contract(api_client, authenticated_api) -> None:
    catalog = await api_client.get("/v1/api-keys/permissions", headers=AUTH)
    assert catalog.status_code == 200
    assert catalog.json()["results"][0]["id"] == "chat.read"

    listed = await api_client.get("/v1/api-keys", headers=AUTH, params={"project_id": "11111111-1111-1111-1111-111111111111"})
    assert listed.status_code == 200
    assert_paginated(listed.json())

    created = await api_client.post(
        "/v1/api-keys",
        headers=AUTH,
        params={"project_id": "11111111-1111-1111-1111-111111111111"},
        json={"name": "Key 1", "description": "desc", "permissions": ["chat.read"]},
    )
    assert created.status_code == 201
    assert created.json()["key"].startswith("sk_")

    detail = await api_client.get("/v1/api-keys/api-key-1", headers=AUTH)
    assert detail.status_code == 200
    assert detail.json()["api_key_uuid"] == "api-key-1"

    updated = await api_client.put(
        "/v1/api-keys/api-key-1",
        headers=AUTH,
        json={"name": "Key 2", "description": "changed", "permissions": ["chat.read"]},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Key 2"

    disabled = await api_client.post("/v1/api-keys/api-key-1/disable", headers=AUTH)
    assert disabled.status_code == 200
    assert disabled.json()["disabled"] is True

    enabled = await api_client.post("/v1/api-keys/api-key-1/enable", headers=AUTH)
    assert enabled.status_code == 200
    assert enabled.json()["disabled"] is False

    deleted = await api_client.delete("/v1/api-keys/api-key-1", headers=AUTH)
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_admin_dashboard_users_and_permission_write_contract(api_client, authenticated_api) -> None:
    me = await api_client.get("/v1/admin/me", headers=AUTH)
    assert me.status_code == 200
    assert me.json()["id"] == "admin-1"

    summary = await api_client.get("/v1/admin/dashboard/summary", headers=AUTH)
    assert summary.status_code == 200
    assert summary.json() == {"organizations": 1, "projects": 2, "api_keys": 3, "users": 4}

    users = await api_client.get("/v1/admin/users", headers=AUTH, params={"limit": 7, "offset": 3, "q": "alice"})
    assert users.status_code == 200
    assert_paginated(users.json())
    pagination = authenticated_api["admin"].calls[-1][1]
    assert pagination.limit == 7
    assert pagination.offset == 3
    assert pagination.q == "alice"

    profile = await api_client.get("/v1/admin/user-profiles/user-1", headers=AUTH)
    assert profile.status_code == 200
    assert profile.json()["permissions"]["project_permissions"] == []

    set_permissions = await api_client.put(
        "/v1/admin/user-permissions/user-1",
        headers=AUTH,
        json={"organization_permissions": ["organization.settings.read"], "project_permissions": []},
    )
    assert set_permissions.status_code == 200
    assert set_permissions.json()["permissions"][
        "organization_permissions"
    ] == ["organization.settings.read"]

    reset = await api_client.delete("/v1/admin/user-permissions/user-1", headers=AUTH)
    assert reset.status_code == 200
    assert reset.json()["permissions"]["organization_permissions"] == []
