from __future__ import annotations

import pytest

from tests.api.fakes import PROJECT_UUID
from tests.helpers.http import assert_paginated

pytestmark = pytest.mark.api

AUTH = {"Authorization": "Bearer test-token"}
ADMIN_AUTH = {"Authorization": "Bearer admin-token"}


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
        "/v1/admin/user-permissions/user-1",
        headers=ADMIN_AUTH,
        json={
            "organization_permissions": ["organization.settings.read"],
            "project_permissions": [
                {"project_id": PROJECT_UUID, "permissions": ["project.settings.read"]}
            ],
        },
    )
    assert permission_update.status_code == 200
    project_permissions = permission_update.json()["permissions"]["project_permissions"]
    assert project_permissions == [
        {
            "id": PROJECT_UUID,
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
