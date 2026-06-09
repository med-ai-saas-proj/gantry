from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from pyrusult import ResultStatus

from tests.helpers.auth import bearer, password_token

pytestmark = pytest.mark.integration


@pytest.fixture
async def management_api_client(integration_config_file):
    from gantry.main.app import main_app

    transport = httpx.ASGITransport(
        app=main_app,
        raise_app_exceptions=False,
    )
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://integration-management.test",
    ) as client:
        yield client


def _assert_not_server_error(response: httpx.Response) -> None:
    assert response.status_code < 500, response.text


async def _organization_id_from_token(token: str) -> str:
    from gantry.management.auth.factories import getAuthService

    return (await getAuthService().verifyToken(token)).unwrap()["org_uuid"]


@pytest.fixture
def real_user_token(integration_stack) -> str:
    token = password_token(
        "gantry-test-user",
        "password",
        "gantry-frontend",
        scope="openid profile email organization:*",
        keycloak_url=integration_stack.keycloak_url,
    )
    return token["access_token"]


@pytest.fixture
def real_admin_token(integration_stack) -> str:
    token = password_token(
        "gantry-admin-user",
        "password",
        "gantry-admin",
        keycloak_url=integration_stack.keycloak_url,
    )
    return token["access_token"]


@pytest.mark.asyncio
async def test_management_api_auth_and_admin_story_uses_real_keycloak(
    management_api_client: httpx.AsyncClient,
    migrated_management_storage,
    real_user_token: str,
    real_admin_token: str,
) -> None:
    _ = migrated_management_storage
    missing_auth = await management_api_client.get("/management/v1/projects")
    _assert_not_server_error(missing_auth)
    assert missing_auth.status_code in {401, 403}

    normal_user_admin = await management_api_client.get(
        "/management/v1/admin/me",
        headers=bearer(real_user_token),
    )
    _assert_not_server_error(normal_user_admin)
    assert normal_user_admin.status_code in {401, 403}

    admin_me = await management_api_client.get(
        "/management/v1/admin/me",
        headers=bearer(real_admin_token),
    )
    assert admin_me.status_code == 200, admin_me.text
    admin_payload = admin_me.json()
    assert admin_payload["user_id"]
    assert admin_payload["email"] == "admin-user@gantry.com"

    dashboard = await management_api_client.get(
        "/management/v1/admin/dashboard/summary",
        headers=bearer(real_admin_token),
    )
    assert dashboard.status_code == 200, dashboard.text
    assert set(dashboard.json()) == {
        "organizations",
        "projects",
        "api_keys",
        "users",
    }


@pytest.mark.asyncio
async def test_management_project_and_api_key_flow_crosses_auth_db_and_cache(
    management_api_client: httpx.AsyncClient,
    migrated_management_storage,
    integration_stack,
    real_user_token: str,
) -> None:
    assert integration_stack.timescale_asyncpg_uri
    assert integration_stack.redis_url
    headers = bearer(real_user_token)
    org_id = await _organization_id_from_token(real_user_token)
    suffix = uuid4().hex[:10]

    org_settings = await management_api_client.patch(
        f"/management/v1/organizations/{org_id}/settings",
        headers=headers,
        json={
            "rate_limit": 1000,
            "spending_limit": 500,
            "extra": {"integration": "management-api", "run": suffix},
        },
    )
    assert org_settings.status_code == 200, org_settings.text
    assert org_settings.json()["rate_limit"] == 1000

    create_project = await management_api_client.post(
        "/management/v1/projects",
        params={"organization": org_id},
        headers=headers,
        json={
            "name": f"Integration HTTP Project {suffix}",
            "description": "Created through the management API integration story",
        },
    )
    assert create_project.status_code == 201, create_project.text
    project = create_project.json()
    project_uuid = project["project_uuid"]
    assert project["organization_id"] == org_id

    update_project_settings = await management_api_client.patch(
        f"/management/v1/projects/{project_uuid}/settings",
        headers=headers,
        json={
            "rate_limit": 250,
            "spending_limit": 125,
            "extra": {"integration": "project-settings"},
        },
    )
    assert update_project_settings.status_code == 200, update_project_settings.text
    assert update_project_settings.json()["rate_limit"] == 250

    create_key = await management_api_client.post(
        "/management/v1/api-keys",
        params={"project_id": project_uuid},
        headers=headers,
        json={
            "name": f"integration-http-key-{suffix}",
            "description": "Created through HTTP integration story",
            "permissions": ["chat.read", "conversation.read"],
        },
    )
    assert create_key.status_code == 201, create_key.text
    api_key = create_key.json()
    api_key_uuid = api_key["api_key_uuid"]
    raw_key = api_key["key"]
    assert api_key["project_uuid"] == project_uuid
    assert raw_key.startswith("sk_")

    list_keys = await management_api_client.get(
        "/management/v1/api-keys",
        params={"project_id": project_uuid},
        headers=headers,
    )
    assert list_keys.status_code == 200, list_keys.text
    assert any(
        item["api_key_uuid"] == api_key_uuid
        for item in list_keys.json()["results"]
    )

    disable_key = await management_api_client.post(
        f"/management/v1/api-keys/{api_key_uuid}/disable",
        headers=headers,
    )
    assert disable_key.status_code == 200, disable_key.text
    assert disable_key.json()["disabled"] is True

    from gantry.management.api_key.factories import getApiKeyService

    disabled_parse = await getApiKeyService().parseApiKey(raw_key)
    assert disabled_parse.status == ResultStatus.Err

    enable_key = await management_api_client.post(
        f"/management/v1/api-keys/{api_key_uuid}/enable",
        headers=headers,
    )
    assert enable_key.status_code == 200, enable_key.text
    assert enable_key.json()["disabled"] is False

    enabled_parse = await getApiKeyService().parseApiKey(raw_key)
    assert enabled_parse.status == ResultStatus.Ok
    parsed = enabled_parse.unwrap()
    assert parsed["project_uuid"] == project_uuid
    assert parsed["organization_uuid"] == org_id
    assert parsed["rpm_limit_organization"] == 1000
    assert parsed["rpm_limit_project"] == 250
    assert parsed["spending_limit_organization"] == 500
    assert parsed["spending_limit_project"] == 125

    delete_key = await management_api_client.delete(
        f"/management/v1/api-keys/{api_key_uuid}",
        headers=headers,
    )
    assert delete_key.status_code == 200, delete_key.text

    deleted_parse = await getApiKeyService().parseApiKey(raw_key)
    assert deleted_parse.status == ResultStatus.Err


@pytest.mark.asyncio
async def test_admin_scoped_permission_routes_update_keycloak_without_clobbering_other_scopes(
    management_api_client: httpx.AsyncClient,
    migrated_management_storage,
    real_user_token: str,
    real_admin_token: str,
) -> None:
    _ = migrated_management_storage
    admin_headers = bearer(real_admin_token)
    org_id = await _organization_id_from_token(real_user_token)
    suffix = uuid4().hex[:10]

    users = await management_api_client.get(
        "/management/v1/admin/users",
        params={"q": "gantry-test-user"},
        headers=admin_headers,
    )
    assert users.status_code == 200, users.text
    user_id = next(
        item["user_id"]
        for item in users.json()["results"]
        if item.get("username") == "gantry-test-user"
    )

    create_project = await management_api_client.post(
        "/management/v1/admin/projects",
        params={"org_id": org_id},
        headers=admin_headers,
        json={
            "name": f"Integration Scoped Permission {suffix}",
            "description": "Created for admin scoped permission route coverage",
        },
    )
    assert create_project.status_code == 201, create_project.text
    project_uuid = create_project.json()["project_uuid"]

    org_update = await management_api_client.put(
        f"/management/v1/admin/organizations/{org_id}/users/{user_id}/permissions",
        headers=admin_headers,
        json={"permissions": ["organization.owner"]},
    )
    assert org_update.status_code == 200, org_update.text
    org_summary = org_update.json()["permissions"]
    assert org_summary["organization_permissions"] == ["organization.owner"]

    project_update = await management_api_client.put(
        f"/management/v1/admin/projects/{project_uuid}/users/{user_id}/permissions",
        headers=admin_headers,
        json={"permissions": ["project.settings.read", "apikey.read"]},
    )
    assert project_update.status_code == 200, project_update.text
    project_summary = project_update.json()["permissions"]
    assert project_summary["organization_permissions"] == ["organization.owner"]
    assert any(
        item["project_uuid"] == project_uuid
        and set(item["permissions"]) == {"project.settings.read", "apikey.read"}
        for item in project_summary["project_permissions"]
    )

    fetched = await management_api_client.get(
        f"/management/v1/admin/users/{user_id}/permissions",
        headers=admin_headers,
    )
    assert fetched.status_code == 200, fetched.text
    fetched_summary = fetched.json()
    assert fetched_summary["organization_permissions"] == ["organization.owner"]
    assert any(
        item["project_uuid"] == project_uuid
        for item in fetched_summary["project_permissions"]
    )


@pytest.mark.asyncio
async def test_admin_project_api_key_and_user_profile_flow_uses_real_keycloak_db_and_cache(
    management_api_client: httpx.AsyncClient,
    migrated_management_storage,
    real_user_token: str,
    real_admin_token: str,
) -> None:
    _ = migrated_management_storage
    admin_headers = bearer(real_admin_token)
    org_id = await _organization_id_from_token(real_user_token)
    suffix = uuid4().hex[:10]

    users = await management_api_client.get(
        "/management/v1/admin/users",
        params={"q": "gantry-test-user"},
        headers=admin_headers,
    )
    assert users.status_code == 200, users.text
    user_id = next(
        item["user_id"]
        for item in users.json()["results"]
        if item.get("username") == "gantry-test-user"
    )

    profile = await management_api_client.get(
        f"/management/v1/admin/users/{user_id}/profile",
        headers=admin_headers,
    )
    organizations = await management_api_client.get(
        f"/management/v1/admin/users/{user_id}/organizations",
        headers=admin_headers,
    )
    permissions = await management_api_client.get(
        f"/management/v1/admin/users/{user_id}/permissions",
        headers=admin_headers,
    )
    org_users = await management_api_client.get(
        f"/management/v1/admin/organizations/{org_id}/users",
        headers=admin_headers,
    )

    assert profile.status_code == 200, profile.text
    assert profile.json()["user_id"] == user_id
    assert organizations.status_code == 200, organizations.text
    assert any(item["org_id"] == org_id for item in organizations.json())
    assert permissions.status_code == 200, permissions.text
    assert "organization_permissions" in permissions.json()
    assert org_users.status_code == 200, org_users.text

    create_project = await management_api_client.post(
        "/management/v1/admin/projects",
        params={"org_id": org_id},
        headers=admin_headers,
        json={
            "name": f"Integration Admin API Key {suffix}",
            "description": "Created by admin integration flow",
        },
    )
    assert create_project.status_code == 201, create_project.text
    project_uuid = create_project.json()["project_uuid"]

    project_users = await management_api_client.get(
        f"/management/v1/admin/projects/{project_uuid}/users",
        headers=admin_headers,
    )
    assert project_users.status_code == 200, project_users.text

    create_key = await management_api_client.post(
        "/management/v1/admin/api-keys",
        params={"project_id": project_uuid},
        headers=admin_headers,
        json={
            "name": f"admin-integration-key-{suffix}",
            "description": "Created through admin integration story",
            "permissions": ["chat.read", "conversation.read"],
        },
    )
    assert create_key.status_code == 201, create_key.text
    api_key_uuid = create_key.json()["api_key_uuid"]

    update_disabled = await management_api_client.put(
        f"/management/v1/admin/api-keys/{api_key_uuid}",
        headers=admin_headers,
        json={
            "name": f"admin-integration-key-{suffix}-disabled",
            "description": "disabled through admin integration story",
            "permissions": ["chat.read"],
            "disabled": True,
        },
    )
    assert update_disabled.status_code == 200, update_disabled.text
    assert update_disabled.json()["disabled"] is True

    list_disabled = await management_api_client.get(
        "/management/v1/admin/api-keys",
        params={"project_id": project_uuid, "disabled": True},
        headers=admin_headers,
    )
    get_disabled = await management_api_client.get(
        f"/management/v1/admin/api-keys/{api_key_uuid}",
        params={"disabled": True},
        headers=admin_headers,
    )
    assert list_disabled.status_code == 200, list_disabled.text
    assert any(
        item["api_key_uuid"] == api_key_uuid and item["disabled"] is True
        for item in list_disabled.json()["results"]
    )
    assert get_disabled.status_code == 200, get_disabled.text
    assert get_disabled.json()["api_key_uuid"] == api_key_uuid
    assert get_disabled.json()["disabled"] is True

    delete_key = await management_api_client.delete(
        f"/management/v1/admin/api-keys/{api_key_uuid}",
        headers=admin_headers,
    )
    assert delete_key.status_code == 200, delete_key.text
