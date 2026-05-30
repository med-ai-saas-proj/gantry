from __future__ import annotations

import pytest

from tests.api.fakes import PROJECT_UUID
from tests.helpers.http import assert_paginated

pytestmark = pytest.mark.api

AUTH = {"Authorization": "Bearer admin-token"}


@pytest.mark.asyncio
async def test_admin_organization_routes(api_client, authenticated_api) -> None:
    permissions = await api_client.get("/v1/admin/organizations/permissions", headers=AUTH)
    assert permissions.status_code == 200

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

    settings = await api_client.get("/v1/admin/organizations/org-1/settings", headers=AUTH)
    assert settings.status_code == 200

    patched_settings = await api_client.patch(
        "/v1/admin/organizations/org-1/settings",
        headers=AUTH,
        json={"rate_limit": 200, "spending_limit": 3000, "extra": {"tier": "team"}},
    )
    assert patched_settings.status_code == 200
    assert patched_settings.json()["extra"] == {"tier": "team"}

    users = await api_client.get(
        "/v1/admin/organizations/org-1/users",
        headers=AUTH,
        params={"limit": 6, "offset": 2, "q": "alice"},
    )
    assert users.status_code == 200
    assert_paginated(users.json())

    delete_org = await api_client.delete("/v1/admin/organizations/org-1", headers=AUTH)
    assert delete_org.status_code == 202
    assert delete_org.json()["id"] == "org-1"


@pytest.mark.asyncio
async def test_admin_project_routes(api_client, authenticated_api) -> None:
    permissions = await api_client.get("/v1/admin/projects/permissions", headers=AUTH)
    assert permissions.status_code == 200

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

    settings = await api_client.get(f"/v1/admin/projects/{PROJECT_UUID}/settings", headers=AUTH)
    assert settings.status_code == 200

    patched_settings = await api_client.patch(
        f"/v1/admin/projects/{PROJECT_UUID}/settings",
        headers=AUTH,
        json={"rate_limit": 120, "spending_limit": 4567, "extra": {"mode": "strict"}},
    )
    assert patched_settings.status_code == 200
    assert patched_settings.json()["spending_limit"] == 4567

    users = await api_client.get(
        f"/v1/admin/projects/{PROJECT_UUID}/users",
        headers=AUTH,
        params={"limit": 3, "offset": 1, "q": "bob"},
    )
    assert users.status_code == 200

    archived = await api_client.post(f"/v1/admin/projects/{PROJECT_UUID}/archive", headers=AUTH)
    assert archived.status_code == 200
    assert archived.json() == {"id": PROJECT_UUID, "archived": True}

    unarchived = await api_client.post(f"/v1/admin/projects/{PROJECT_UUID}/unarchive", headers=AUTH)
    assert unarchived.status_code == 200
    assert unarchived.json() == {"id": PROJECT_UUID, "archived": False}

    delete_archive = await api_client.delete(f"/v1/admin/projects/{PROJECT_UUID}", headers=AUTH)
    assert delete_archive.status_code == 200
    assert delete_archive.json() == {"id": PROJECT_UUID, "archived": True}


@pytest.mark.asyncio
async def test_admin_api_key_routes(api_client, authenticated_api) -> None:
    permissions = await api_client.get("/v1/admin/api-keys/permissions", headers=AUTH)
    assert permissions.status_code == 200

    listed = await api_client.get(
        "/v1/admin/api-keys",
        headers=AUTH,
        params={"project_id": PROJECT_UUID, "disabled": "true"},
    )
    assert listed.status_code == 200
    assert listed.json()["results"][0]["project_uuid"] == PROJECT_UUID
    assert listed.json()["results"][0]["disabled"] is True
    assert authenticated_api["admin"].calls[-1][1] == {
        "project_id": PROJECT_UUID,
        "disabled": True,
    }

    created = await api_client.post(
        "/v1/admin/api-keys",
        headers=AUTH,
        params={"project_id": PROJECT_UUID},
        json={"name": "Admin Key", "description": "desc", "permissions": ["chat.read"]},
    )
    assert created.status_code == 201
    assert created.json()["key"].startswith("sk_")
    assert authenticated_api["admin"].calls[-1][1]["user_info"]["id"] == "admin-1"

    detail = await api_client.get(
        "/v1/admin/api-keys/api-key-1",
        headers=AUTH,
        params={"disabled": "false"},
    )
    assert detail.status_code == 200
    assert detail.json()["api_key_uuid"] == "api-key-1"
    assert authenticated_api["admin"].calls[-1][1] == {
        "api_key_uuid": "api-key-1",
        "disabled": False,
    }

    updated = await api_client.put(
        "/v1/admin/api-keys/api-key-1",
        headers=AUTH,
        json={
            "name": "Updated Key",
            "description": "updated",
            "permissions": ["chat.read"],
            "disabled": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Key"
    assert updated.json()["disabled"] is True

    deleted = await api_client.delete("/v1/admin/api-keys/api-key-1", headers=AUTH)
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_admin_user_profile_permission_and_organization_routes(api_client, authenticated_api) -> None:
    organizations = await api_client.get(
        "/v1/admin/users/user-1/organizations",
        headers=AUTH,
    )
    assert organizations.status_code == 200

    profile = await api_client.get("/v1/admin/users/user-1/profile", headers=AUTH)
    assert profile.status_code == 200

    permissions = await api_client.get(
        "/v1/admin/users/user-1/permissions",
        headers=AUTH,
    )
    assert permissions.status_code == 200
    assert permissions.json()["project_permissions"][0]["project_uuid"] == PROJECT_UUID

    project_permissions = [
        {"project_uuid": PROJECT_UUID, "permissions": ["project.settings.read"]}
    ]
    updated = await api_client.put(
        "/v1/admin/users/user-1/permissions",
        headers=AUTH,
        json={
            "organization_permissions": ["organization.settings.read"],
            "project_permissions": project_permissions,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["permissions"]["project_permissions"][0]["project_uuid"] == PROJECT_UUID

    scoped_org = await api_client.put(
        "/v1/admin/organizations/org-1/users/user-1/permissions",
        headers=AUTH,
        json={"permissions": ["organization.settings.write"]},
    )
    assert scoped_org.status_code == 200
    assert scoped_org.json()["permissions"]["organization_permissions"] == [
        "organization.settings.write"
    ]
    assert authenticated_api["admin"].calls[-1][1] == {
        "user_id": "user-1",
        "org_id": "org-1",
        "permissions": ["organization.settings.write"],
    }

    scoped_project = await api_client.put(
        f"/v1/admin/projects/{PROJECT_UUID}/users/user-1/permissions",
        headers=AUTH,
        json={"permissions": ["project.settings.write"]},
    )
    assert scoped_project.status_code == 200
    assert scoped_project.json()["permissions"]["project_permissions"][0] == {
        "project_uuid": PROJECT_UUID,
        "permissions": ["project.settings.write"],
        "effective_permissions": ["project.settings.write"],
    }
    assert authenticated_api["admin"].calls[-1][1] == {
        "user_id": "user-1",
        "project_id": PROJECT_UUID,
        "permissions": ["project.settings.write"],
    }

    reset = await api_client.delete("/v1/admin/users/user-1/permissions", headers=AUTH)
    assert reset.status_code == 200
    assert reset.json()["permissions"]["project_permissions"] == []
