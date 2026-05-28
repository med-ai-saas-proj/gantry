from __future__ import annotations

import pytest

from tests.regression.helpers import schema_properties

pytestmark = pytest.mark.regression


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
def test_public_management_dto_fields_are_backward_compatible(
    management_openapi: dict,
) -> None:
    actual = {
        schema_name: schema_properties(management_openapi, schema_name)
        for schema_name in REQUIRED_PUBLIC_SCHEMA_FIELDS
    }
    removed = {
        schema_name: required - actual[schema_name]
        for schema_name, required in REQUIRED_PUBLIC_SCHEMA_FIELDS.items()
    }

    assert not any(removed.values()), removed
