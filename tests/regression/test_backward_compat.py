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
    "AdminUserPermissionSummaryResponse": {
        "organization_permissions",
        "effective_organization_permissions",
        "project_permissions",
    },
    "AdminUserProjectPermissionResponse": {
        "project_uuid",
        "permissions",
        "effective_permissions",
    },
    "AdminUserProfileResponse": {
        "user_id",
        "username",
        "email",
        "enabled",
        "email_verified",
        "organizations",
        "permissions",
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


def test_admin_permission_dtos_use_explicit_project_uuid_not_ambiguous_id(
    management_openapi: dict,
) -> None:
    project_permission_fields = schema_properties(
        management_openapi,
        "AdminUserProjectPermissionResponse",
    )
    project_permission_update_fields = schema_properties(
        management_openapi,
        "AdminUserProjectPermissionUpdateRequest",
    )

    assert "project_uuid" in project_permission_fields
    assert "project_uuid" in project_permission_update_fields
    assert "id" not in project_permission_fields
    assert "id" not in project_permission_update_fields
