from __future__ import annotations

import httpx
import pytest

from tests.helpers.auth import bearer, password_token, token_claims
from tests.settings import REALM

pytestmark = pytest.mark.integration


def test_identity_metadata_supports_management_token_validation(
    integration_stack,
) -> None:
    response = httpx.get(integration_stack.identity_metadata_url, timeout=8.0)

    assert response.status_code == 200
    body = response.json()
    assert body["issuer"].endswith("/realms/gantry")
    assert body["token_endpoint"].endswith("/protocol/openid-connect/token")
    assert body["jwks_uri"].endswith("/protocol/openid-connect/certs")


def test_frontend_user_can_obtain_management_identity_token(
    integration_stack,
) -> None:
    token = password_token(
        "gantry-test-user",
        "password",
        "gantry-frontend",
        scope="openid profile email organization:*",
        keycloak_url=integration_stack.keycloak_url,
    )
    claims = token_claims(token["access_token"])

    assert claims["preferred_username"] == "gantry-test-user"
    assert claims["iss"].endswith(f"/realms/{REALM}")
    assert claims["organization"]


def test_admin_user_identity_token_contains_admin_role(
    integration_stack,
) -> None:
    token = password_token(
        "gantry-admin-user",
        "password",
        "gantry-admin",
        keycloak_url=integration_stack.keycloak_url,
    )
    claims = token_claims(token["access_token"])

    assert claims["preferred_username"] == "gantry-admin-user"
    assert "ADMIN" in claims["realm_access"]["roles"]


def test_frontend_user_profile_is_available_after_login(
    integration_stack,
) -> None:
    token = password_token(
        "gantry-test-user",
        "password",
        "gantry-frontend",
        scope="openid profile email organization:*",
        keycloak_url=integration_stack.keycloak_url,
    )
    response = httpx.get(
        f"{integration_stack.keycloak_url}/realms/{REALM}/protocol/openid-connect/userinfo",
        headers=bearer(token["access_token"]),
        timeout=12.0,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["preferred_username"] == "gantry-test-user"
    assert payload["email_verified"] is True


def test_wrong_password_is_rejected_by_identity_provider(
    integration_stack,
) -> None:
    with pytest.raises(httpx.HTTPStatusError):
        password_token(
            "gantry-test-user",
            "wrong-password",
            "gantry-frontend",
            keycloak_url=integration_stack.keycloak_url,
        )


def test_service_client_can_read_permission_attributes_from_realm(
    keycloak_admin_client,
) -> None:
    users = keycloak_admin_client.get_users({"username": "gantry-test-user"})

    assert users
    attributes = users[0].get("attributes", {})
    assert "org_permissions" in attributes
    project_permissions = attributes.get("project_permissions", [])
    assert isinstance(project_permissions, list)


@pytest.mark.asyncio
async def test_management_auth_service_maps_real_token_to_user_info(
    integration_config_file,
    integration_stack,
) -> None:
    from gantry.management.auth.factories import getAuthService

    token = password_token(
        "gantry-test-user",
        "password",
        "gantry-frontend",
        scope="openid profile email organization:*",
        keycloak_url=integration_stack.keycloak_url,
    )
    result = await getAuthService().verifyToken(token["access_token"])

    user_info = result.unwrap()
    assert user_info["id"]
    assert user_info["org_uuid"]
    assert "org_permissions" in user_info
    assert isinstance(user_info["project_permissions"], dict)
