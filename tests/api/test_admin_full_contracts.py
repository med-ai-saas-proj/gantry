from __future__ import annotations

import pytest

from tests.api.fakes import PROJECT_UUID
from tests.helpers.http import assert_paginated

pytestmark = pytest.mark.api

AUTH = {"Authorization": "Bearer admin-token"}


@pytest.mark.asyncio
async def test_admin_organization_routes_and_aliases(api_client, authenticated_api) -> None:
    permissions = await api_client.get("/v1/admin/organization-permissions", headers=AUTH)
    alias_permissions = await api_client.get("/v1/admin/organizations/permissions", headers=AUTH)
    assert permissions.status_code == 200
    assert alias_permissions.status_code == 200
    assert permissions.json() == alias_permissions.json()

    listed = await api_client.get(
        "/v1/admin/organizations",
        headers=AUTH,
        params={"limit": 4, "offset": 1, "q": "org"},
    )
    assert listed.status_code == 200
    assert_paginated(listed.json())
    pagination = authenticated_api["admin"].calls[-1][1]
    assert pagination.limit == 4
    assert pagination.offset == 1
    assert pagination.q == "org"

    created = await api_client.post(
        "/v1/admin/organizations",
        headers=AUTH,
        json={"name": "Created Org", "alias": "created", "owner_id": "user-1"},
    )
    assert created.status_code == 201
    assert created.json()["org_id"] == "org-created"

    detail = await api_client.get("/v1/admin/organizations/org-1", headers=AUTH)
    assert detail.status_code == 200
    assert detail.json()["org_id"] == "org-1"

    updated = await api_client.patch(
        "/v1/admin/organizations/org-1",
        headers=AUTH,
        json={"name": "Renamed Org"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed Org"

    settings = await api_client.get("/v1/admin/organization-settings/org-1", headers=AUTH)
    alias_settings = await api_client.get("/v1/admin/organizations/org-1/settings", headers=AUTH)
    assert settings.status_code == 200
    assert alias_settings.status_code == 200
    assert settings.json() == alias_settings.json()

    patched_settings = await api_client.patch(
        "/v1/admin/organization-settings/org-1",
        headers=AUTH,
        json={"rate_limit": 200, "spending_limit": 3000, "extra": {"tier": "team"}},
    )
    assert patched_settings.status_code == 200
    assert patched_settings.json()["extra"] == {"tier": "team"}

    users = await api_client.get(
        "/v1/admin/organization-users",
        headers=AUTH,
        params={"org_id": "org-1", "limit": 6, "offset": 2, "q": "alice"},
    )
    alias_users = await api_client.get(
        "/v1/admin/organizations/org-1/users",
        headers=AUTH,
        params={"limit": 6, "offset": 2, "q": "alice"},
    )
    assert users.status_code == 200
    assert alias_users.status_code == 200
    assert_paginated(users.json())
    assert users.json() == alias_users.json()

    delete_org = await api_client.delete("/v1/admin/organizations/org-1", headers=AUTH)
    assert delete_org.status_code == 202
    assert delete_org.json()["id"] == "org-1"


@pytest.mark.asyncio
async def test_admin_project_routes_and_aliases(api_client, authenticated_api) -> None:
    permissions = await api_client.get("/v1/admin/project-permissions", headers=AUTH)
    alias_permissions = await api_client.get("/v1/admin/projects/permissions", headers=AUTH)
    assert permissions.status_code == 200
    assert alias_permissions.status_code == 200
    assert permissions.json() == alias_permissions.json()

    listed = await api_client.get("/v1/admin/projects", headers=AUTH, params={"org_id": "org-1"})
    assert listed.status_code == 200
    assert listed.json()["results"][0]["project_uuid"] == PROJECT_UUID

    created = await api_client.post(
        "/v1/admin/projects",
        headers=AUTH,
        params={"org_id": "org-1"},
        json={"name": "Project", "description": "desc"},
    )
    assert created.status_code == 201
    assert created.json()["organization_id"] == "org-1"

    detail = await api_client.get(f"/v1/admin/projects/{PROJECT_UUID}", headers=AUTH)
    assert detail.status_code == 200
    assert detail.json()["project_uuid"] == PROJECT_UUID

    updated = await api_client.put(
        f"/v1/admin/projects/{PROJECT_UUID}",
        headers=AUTH,
        json={"name": "Updated Project", "description": "updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Project"

    settings = await api_client.get(f"/v1/admin/project-settings/{PROJECT_UUID}", headers=AUTH)
    alias_settings = await api_client.get(f"/v1/admin/projects/{PROJECT_UUID}/settings", headers=AUTH)
    assert settings.status_code == 200
    assert alias_settings.status_code == 200
    assert settings.json() == alias_settings.json()

    patched_settings = await api_client.patch(
        f"/v1/admin/project-settings/{PROJECT_UUID}",
        headers=AUTH,
        json={"rate_limit": 120, "spending_limit": 4567, "extra": {"mode": "strict"}},
    )
    assert patched_settings.status_code == 200
    assert patched_settings.json()["spending_limit"] == 4567

    users = await api_client.get(
        "/v1/admin/project-users",
        headers=AUTH,
        params={"project_id": PROJECT_UUID, "limit": 3, "offset": 1, "q": "bob"},
    )
    alias_users = await api_client.get(
        f"/v1/admin/projects/{PROJECT_UUID}/users",
        headers=AUTH,
        params={"limit": 3, "offset": 1, "q": "bob"},
    )
    assert users.status_code == 200
    assert alias_users.status_code == 200
    assert users.json() == alias_users.json()

    archived = await api_client.delete(f"/v1/admin/projects/{PROJECT_UUID}", headers=AUTH)
    assert archived.status_code == 200
    assert archived.json() == {"id": PROJECT_UUID, "archived": True}


@pytest.mark.asyncio
async def test_admin_api_key_routes_and_aliases(api_client, authenticated_api) -> None:
    permissions = await api_client.get("/v1/admin/api-key-permissions", headers=AUTH)
    alias_permissions = await api_client.get("/v1/admin/api-keys/permissions", headers=AUTH)
    assert permissions.status_code == 200
    assert alias_permissions.status_code == 200
    assert permissions.json() == alias_permissions.json()

    listed = await api_client.get(
        "/v1/admin/api-keys",
        headers=AUTH,
        params={"project_id": PROJECT_UUID},
    )
    assert listed.status_code == 200
    assert listed.json()["results"][0]["project_uuid"] == PROJECT_UUID

    created = await api_client.post(
        "/v1/admin/api-keys",
        headers=AUTH,
        params={"project_id": PROJECT_UUID},
        json={"name": "Admin Key", "description": "desc", "permissions": ["chat.read"]},
    )
    assert created.status_code == 201
    assert created.json()["key"].startswith("sk_")
    assert authenticated_api["admin"].calls[-1][1]["user_info"]["id"] == "admin-1"

    detail = await api_client.get("/v1/admin/api-keys/api-key-1", headers=AUTH)
    assert detail.status_code == 200
    assert detail.json()["api_key_uuid"] == "api-key-1"

    updated = await api_client.put(
        "/v1/admin/api-keys/api-key-1",
        headers=AUTH,
        json={"name": "Updated Key", "description": "updated", "permissions": ["chat.read"]},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Key"

    deleted = await api_client.delete("/v1/admin/api-keys/api-key-1", headers=AUTH)
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_admin_user_profile_permission_and_organization_aliases(api_client, authenticated_api) -> None:
    organizations = await api_client.get(
        "/v1/admin/user-organizations",
        headers=AUTH,
        params={"user_id": "user-1"},
    )
    alias_organizations = await api_client.get(
        "/v1/admin/users/user-1/organizations",
        headers=AUTH,
    )
    assert organizations.status_code == 200
    assert alias_organizations.status_code == 200
    assert organizations.json() == alias_organizations.json()

    profile = await api_client.get("/v1/admin/user-profiles/user-1", headers=AUTH)
    alias_profile = await api_client.get("/v1/admin/users/user-1/profile", headers=AUTH)
    assert profile.status_code == 200
    assert alias_profile.status_code == 200
    assert profile.json() == alias_profile.json()

    project_permissions = [
        {"project_id": PROJECT_UUID, "permissions": ["project.settings.read"]}
    ]
    updated = await api_client.put(
        "/v1/admin/users/user-1/permissions",
        headers=AUTH,
        json={
            "organization_permissions": ["organization.settings.read"],
            "project_permissions": project_permissions,
        },
    )
    canonical_updated = await api_client.put(
        "/v1/admin/user-permissions/user-1",
        headers=AUTH,
        json={
            "organization_permissions": ["organization.settings.read"],
            "project_permissions": project_permissions,
        },
    )
    assert updated.status_code == 200
    assert canonical_updated.status_code == 200
    assert updated.json()["permissions"] == canonical_updated.json()["permissions"]
    assert updated.json()["permissions"]["project_permissions"][0]["id"] == PROJECT_UUID

    reset = await api_client.delete("/v1/admin/users/user-1/permissions", headers=AUTH)
    assert reset.status_code == 200
    assert reset.json()["permissions"]["project_permissions"] == []
