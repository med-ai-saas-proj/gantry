from __future__ import annotations

import pytest

from tests.api.fakes import PROJECT_UUID

pytestmark = pytest.mark.api

AUTH = {"Authorization": "Bearer admin-token"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("post", "/v1/admin/organizations", {"name": ""}),
        ("patch", "/v1/admin/organizations/org-1", {"name": ""}),
        ("post", "/v1/admin/projects?org_id=org-1", {"name": ""}),
        ("put", f"/v1/admin/projects/{PROJECT_UUID}", {"name": ""}),
        ("patch", f"/v1/admin/project-settings/{PROJECT_UUID}", {"rate_limit": 0}),
        ("post", f"/v1/admin/api-keys?project_id={PROJECT_UUID}", {"name": ""}),
        ("put", "/v1/admin/api-keys/api-key-1", {"name": ""}),
    ],
)
async def test_admin_invalid_bodies_return_422(
    api_client,
    authenticated_api,
    method: str,
    path: str,
    json_body: dict,
) -> None:
    response = await getattr(api_client, method)(path, headers=AUTH, json=json_body)

    assert response.status_code in {400, 422}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/v1/admin/projects",
        "/v1/admin/project-users",
        "/v1/admin/api-keys",
        "/v1/admin/organization-users",
        "/v1/admin/user-organizations",
    ],
)
async def test_admin_missing_required_query_params_return_422(
    api_client,
    authenticated_api,
    path: str,
) -> None:
    response = await api_client.get(path, headers=AUTH)

    assert response.status_code in {400, 422}
