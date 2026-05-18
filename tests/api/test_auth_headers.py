from __future__ import annotations

import pytest

from gantry.management.api_key.factories import getApiKeyService
from gantry.management.auth.dependencies import getUserInfo

pytestmark = pytest.mark.api


class FakeApiKeyService:
    def getPermissionCatalog(self) -> dict:
        return {
            "total": 1,
            "results": [
                {
                    "id": "chat.read",
                    "name": "Chat Read",
                    "description": "Allow reading chat resources",
                }
            ],
        }


@pytest.mark.asyncio
async def test_api_key_permissions_requires_authorization_header(api_client) -> None:
    response = await api_client.get("/v1/api-keys/permissions")

    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_api_key_permissions_accepts_overridden_authenticated_user(
    api_client, override_dependencies, fake_user_info
) -> None:
    override_dependencies[getUserInfo] = lambda: fake_user_info
    override_dependencies[getApiKeyService] = lambda: FakeApiKeyService()

    response = await api_client.get(
        "/v1/api-keys/permissions",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["id"] == "chat.read"
