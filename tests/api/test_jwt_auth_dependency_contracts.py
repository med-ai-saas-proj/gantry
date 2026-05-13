from __future__ import annotations

from typing import Any

import pytest
from pyrusult import Err, Ok

from gantry.management.admin.factories import getAdminService
from gantry.management.auth.factories import getAdminAuthService, getAuthService
from gantry.management.auth.services import ForbiddenError, UnauthorizedError
from gantry.management.project.factories import getProjectService
from tests.factories import AdminInfoFactory, UserInfoFactory
from tests.helpers.auth import forge_jwt, decode_forged_jwt

pytestmark = pytest.mark.api


class JwtBackedAuthService:
    """Fast auth service double that verifies PyJWT tokens without Keycloak."""

    def __init__(self, *, secret: str = "test-secret") -> None:
        self.secret = secret
        self.calls: list[tuple[str, dict[str, Any] | str]] = []

    async def verifyToken(self, token: str):
        try:
            claims = decode_forged_jwt(token, secret=self.secret)
        except Exception as exc:
            return Err(UnauthorizedError(from_exception=exc))
        self.calls.append(("verifyToken", claims))
        return Ok(
            UserInfoFactory(
                id=claims["sub"],
                username=claims.get("name"),
                email=claims.get("email"),
                org_uuid=claims.get("organization", {}).get("id", ""),
            )
        )

    def verifyTokenAdmin(self, token: str):
        try:
            claims = decode_forged_jwt(token, secret=self.secret)
        except Exception as exc:
            return Err(UnauthorizedError(from_exception=exc))
        self.calls.append(("verifyTokenAdmin", claims))
        roles = claims.get("realm_access", {}).get("roles", [])
        if "ADMIN" not in roles:
            return Err(ForbiddenError())
        return Ok(
            AdminInfoFactory(
                id=claims["sub"],
                username=claims.get("name"),
                email=claims.get("email"),
            )
        )


@pytest.mark.asyncio
async def test_user_route_accepts_forged_jwt_through_auth_dependency(
    api_client,
    override_dependencies,
    fake_project_service,
) -> None:
    auth_service = JwtBackedAuthService()
    override_dependencies[getAuthService] = lambda: auth_service
    override_dependencies[getProjectService] = lambda: fake_project_service

    token = forge_jwt({"sub": "jwt-user", "name": "JWT User"})
    response = await api_client.get(
        "/v1/projects",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert auth_service.calls[0][0] == "verifyToken"
    assert fake_project_service.calls[-1] == (
        "listUserProjects",
        {"actor_user_id": "jwt-user"},
    )


@pytest.mark.asyncio
async def test_user_route_rejects_invalid_forged_jwt(
    api_client,
    override_dependencies,
    fake_project_service,
) -> None:
    override_dependencies[getAuthService] = lambda: JwtBackedAuthService()
    override_dependencies[getProjectService] = lambda: fake_project_service

    response = await api_client.get(
        "/v1/projects",
        headers={"Authorization": "Bearer not-a-jwt"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_admin_route_requires_admin_realm_role_from_forged_jwt(
    api_client,
    override_dependencies,
    fake_admin_service,
) -> None:
    auth_service = JwtBackedAuthService()
    override_dependencies[getAdminAuthService] = lambda: auth_service
    override_dependencies[getAdminService] = lambda: fake_admin_service

    normal_token = forge_jwt({"sub": "normal-user", "realm_access": {"roles": []}})
    normal_response = await api_client.get(
        "/v1/admin/me",
        headers={"Authorization": f"Bearer {normal_token}"},
    )

    admin_token = forge_jwt(
        {"sub": "admin-user", "realm_access": {"roles": ["ADMIN"]}}
    )
    admin_response = await api_client.get(
        "/v1/admin/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert normal_response.status_code == 403
    assert admin_response.status_code == 200
    assert admin_response.json()["id"] == "admin-user"
    assert [call[0] for call in auth_service.calls] == [
        "verifyTokenAdmin",
        "verifyTokenAdmin",
    ]
