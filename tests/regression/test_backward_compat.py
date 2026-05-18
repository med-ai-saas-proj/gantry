from __future__ import annotations

import pytest
from deepdiff import DeepDiff

from tests.regression.helpers import schema_properties

pytestmark = pytest.mark.regression


REMOVED_PUBLIC_MANAGEMENT_PATHS = {
    "/v1/api-keys/{api_key_id}",
    "/v1/projects/{project_id}",
}
REQUIRED_PUBLIC_MANAGEMENT_PATHS = {
    "/v1/api-keys/{api_key_uuid}",
    "/v1/projects/{project_uuid}",
}
REQUIRED_SERVICE_PATHS = {
    "/v1/conversations/{conversation_uid}",
    "/v1/file-storage/service/{file_id}",
    "/v1/file-storage/user/{file_id}",
    "/v1/rag/service/files",
    "/v1/rag/user/files",
}
REQUIRED_INTERNAL_PATHS = {
    "/billing/",
    "/billing/{transaction_uid}/capture",
    "/billing/credits/{org_id}/available",
    "/billing/invoices/{invoice_uid}",
}
REQUIRED_PUBLIC_SCHEMA_FIELDS = {
    "ApiKeyResponse": {
        "api_key_uuid",
        "project_uuid",
        "name",
        "description",
        "hint",
        "created_at",
        "permissions",
        "disabled",
    },
    "ProjectInfoResponse": {"project_uuid", "name", "description", "organization_id", "archived"},
    "OrgInfoResponse": {"org_id", "name", "owner_id"},
    "AdminDashboardSummaryResponse": {
        "organizations",
        "projects",
        "api_keys",
        "users",
    },
}


@pytest.mark.order(2)
def test_ambiguous_public_id_paths_are_not_reintroduced(management_paths: dict) -> None:
    diff = DeepDiff(
        {},
        {
            path: management_paths[path]
            for path in REMOVED_PUBLIC_MANAGEMENT_PATHS
            if path in management_paths
        },
        ignore_order=True,
    )

    assert not diff


@pytest.mark.order(2)
def test_canonical_uuid_paths_still_exist(management_paths: dict) -> None:
    missing = REQUIRED_PUBLIC_MANAGEMENT_PATHS - set(management_paths)

    assert not missing


@pytest.mark.order(2)
def test_service_and_internal_canonical_paths_still_exist(
    service_paths: dict,
    internal_paths: dict,
) -> None:
    missing_service = REQUIRED_SERVICE_PATHS - set(service_paths)
    missing_internal = REQUIRED_INTERNAL_PATHS - set(internal_paths)

    assert not missing_service
    assert not missing_internal


@pytest.mark.order(2)
def test_public_management_dto_fields_are_backward_compatible(
    management_openapi: dict,
) -> None:
    actual = {
        schema_name: schema_properties(management_openapi, schema_name)
        for schema_name in REQUIRED_PUBLIC_SCHEMA_FIELDS
    }
    diff = DeepDiff(
        REQUIRED_PUBLIC_SCHEMA_FIELDS,
        actual,
        ignore_order=True,
        exclude_regex_paths={r"root\['[^']+'\]\[[0-9]+\]"},
    )

    removed = {
        schema_name: required - actual[schema_name]
        for schema_name, required in REQUIRED_PUBLIC_SCHEMA_FIELDS.items()
    }
    assert not any(removed.values()), diff
