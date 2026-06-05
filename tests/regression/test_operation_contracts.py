from __future__ import annotations

import json

import pytest

from tests.regression.helpers import operation_contracts

pytestmark = pytest.mark.regression


@pytest.mark.order(1)
@pytest.mark.parametrize(
    ("app_name", "openapi_fixture", "snapshot_name"),
    [
        ("management", "management_openapi", "management_operation_contracts.json"),
        ("service", "service_openapi", "service_operation_contracts.json"),
        ("gateway", "gateway_openapi", "gateway_operation_contracts.json"),
        ("internal", "internal_openapi", "internal_operation_contracts.json"),
    ],
)
def test_operation_contracts_match_snapshots(
    request,
    snapshot,
    repo_root,
    app_name: str,
    openapi_fixture: str,
    snapshot_name: str,
) -> None:
    openapi = request.getfixturevalue(openapi_fixture)
    snapshot.snapshot_dir = repo_root / "tests" / "snapshots"

    snapshot.assert_match(
        json.dumps(operation_contracts(openapi), indent=2, sort_keys=True) + "\n",
        snapshot_name,
    )


def test_admin_paths_use_nested_module_convention(management_paths: dict) -> None:
    canonical_paths = {
        "/v1/admin/organizations/permissions",
        "/v1/admin/organizations/{org_id}/settings",
        "/v1/admin/organizations/{org_id}/users",
        "/v1/admin/projects/permissions",
        "/v1/admin/projects/{project_id}/settings",
        "/v1/admin/projects/{project_id}/users",
        "/v1/admin/api-keys/permissions",
        "/v1/admin/users/{user_id}/organizations",
        "/v1/admin/users/{user_id}/profile",
        "/v1/admin/users/{user_id}/permissions",
    }
    removed_aliases = {
        "/v1/admin/organization-permissions",
        "/v1/admin/organization-settings/{org_id}",
        "/v1/admin/organization-users",
        "/v1/admin/project-permissions",
        "/v1/admin/project-settings/{project_id}",
        "/v1/admin/project-users",
        "/v1/admin/api-key-permissions",
        "/v1/admin/user-organizations",
        "/v1/admin/user-profiles/{user_id}",
        "/v1/admin/user-permissions/{user_id}",
    }

    assert canonical_paths <= set(management_paths)
    assert not (removed_aliases & set(management_paths))
