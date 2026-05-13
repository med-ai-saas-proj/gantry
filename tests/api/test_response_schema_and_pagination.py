from __future__ import annotations

import pytest

from gantry.management.admin.factories import getAdminService
from gantry.management.auth.dependencies import getAdminInfo
from tests.helpers.http import assert_paginated

pytestmark = pytest.mark.api


class FakeAdminService:
    def __init__(self) -> None:
        self.pagination = None

    async def listUsers(self, pagination) -> dict:
        self.pagination = pagination
        return {
            "total": 1,
            "results": [
                {
                    "id": "user-1",
                    "username": "alice",
                    "email": "alice@example.com",
                    "first_name": "Alice",
                    "last_name": "Example",
                    "enabled": True,
                    "email_verified": True,
                }
            ],
        }


@pytest.mark.asyncio
async def test_admin_user_list_status_schema_and_pagination(
    api_client, override_dependencies, fake_admin_info
) -> None:
    fake_service = FakeAdminService()
    override_dependencies[getAdminInfo] = lambda: fake_admin_info
    override_dependencies[getAdminService] = lambda: fake_service

    response = await api_client.get(
        "/v1/admin/users",
        params={"limit": 5, "offset": 10, "q": "alice"},
        headers={"Authorization": "Bearer admin-token"},
    )

    assert response.status_code == 200
    results = assert_paginated(response.json())
    assert results[0]["id"] == "user-1"
    assert fake_service.pagination.limit == 5
    assert fake_service.pagination.offset == 10
    assert fake_service.pagination.q == "alice"
