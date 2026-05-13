from __future__ import annotations

import pytest

pytestmark = pytest.mark.api

AUTH = {"Authorization": "Bearer test-token"}
PROJECT_UUID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("post", "/v1/projects?organization=org-1", {"name": ""}),
        ("patch", "/v1/projects/11111111-1111-1111-1111-111111111111/settings", {"rate_limit": 0}),
        ("post", "/v1/api-keys?project_id=11111111-1111-1111-1111-111111111111", {"name": ""}),
        ("patch", "/v1/organizations/org-1/settings", {"rate_limit": 0}),
        ("put", "/v1/admin/user-permissions/user-1", {"project_permissions": [{"permissions": ["project.owner"]}]}),
    ],
)
async def test_invalid_request_bodies_return_422(
    api_client,
    authenticated_api,
    method: str,
    path: str,
    json_body: dict,
) -> None:
    response = await getattr(api_client, method)(path, headers=AUTH, json=json_body)

    assert response.status_code in {400, 422}


@pytest.mark.asyncio
async def test_project_uuid_path_rejects_non_uuid_for_permissioned_routes(
    api_client,
    authenticated_api,
) -> None:
    response = await api_client.put(
        "/v1/projects/not-a-uuid",
        headers=AUTH,
        json={"name": "Project", "description": "desc"},
    )

    assert response.status_code in {400, 422}


@pytest.mark.asyncio
async def test_admin_route_rejects_missing_admin_token(api_client) -> None:
    response = await api_client.get("/v1/admin/dashboard/summary")

    assert response.status_code in {401, 403}
