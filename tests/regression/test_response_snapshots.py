from __future__ import annotations

import json

import pytest

from tests.regression.helpers import selected_schemas

pytestmark = pytest.mark.regression


MANAGEMENT_SCHEMAS = [
    "AdminDashboardSummaryResponse",
    "AdminUserProfileResponse",
    "ApiKeyResponse",
    "ApiKeyCreateResponse",
    "OrgInfoResponse",
    "OrgSettingsResponse",
    "ProjectInfoResponse",
    "ProjectSettingsResponse",
    "PermissionCatalogResponse",
    "ProjectPermissionCatalogResponse",
    "ApiKeyPermissionCatalogResponse",
]
SERVICE_SCHEMAS = [
    "CreateConversationResponse",
    "ConversationMetadataResponse",
    "ResponseMessageResponse",
    "FileInfoResponse",
    "FileUploadResponse",
    "FilePresignedURLResponse",
    "RagQueryResponse",
    "EmbeddingTaskResponse",
]
INTERNAL_SCHEMAS = [
    "PostRequest",
    "CaptureRequest",
    "CreditInfoResponse",
    "InvoiceInfoResponse",
    "InvoiceDetailInfoResponse",
]
GATEWAY_SCHEMAS = ["HTTPValidationError", "ValidationError"]


def test_management_openapi_paths_match_snapshot(
    management_paths: dict, snapshot, repo_root
) -> None:
    snapshot.snapshot_dir = repo_root / "tests" / "snapshots"
    actual = "\n".join(sorted(management_paths)) + "\n"

    snapshot.assert_match(actual, "management_paths.txt")


@pytest.mark.order(1)
@pytest.mark.parametrize(
    ("openapi_fixture", "schema_names", "snapshot_name"),
    [
        ("management_openapi", MANAGEMENT_SCHEMAS, "selected_response_schemas.json"),
        ("service_openapi", SERVICE_SCHEMAS, "selected_service_response_schemas.json"),
        ("internal_openapi", INTERNAL_SCHEMAS, "selected_internal_response_schemas.json"),
        ("gateway_openapi", GATEWAY_SCHEMAS, "gateway_proxy_contract.json"),
    ],
)
def test_selected_response_schemas_match_snapshots(
    request,
    snapshot,
    repo_root,
    openapi_fixture: str,
    schema_names: list[str],
    snapshot_name: str,
) -> None:
    openapi = request.getfixturevalue(openapi_fixture)
    snapshot.snapshot_dir = repo_root / "tests" / "snapshots"

    snapshot.assert_match(
        json.dumps(
            selected_schemas(openapi, schema_names),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        snapshot_name,
    )


def test_permission_catalogs_match_snapshot(snapshot, repo_root) -> None:
    from gantry.management.api_key.settings import getApiKeysSettings
    from gantry.management.organization.permissions import (
        ALL_PERMISSIONS as ORGANIZATION_PERMISSIONS,
    )
    from gantry.management.project.permissions import (
        ALL_PERMISSIONS as PROJECT_PERMISSIONS,
    )

    snapshot.snapshot_dir = repo_root / "tests" / "snapshots"
    actual = {
        "api_key": [
            permission.id for permission in getApiKeysSettings().permissions
        ],
        "organization": list(ORGANIZATION_PERMISSIONS),
        "project": list(PROJECT_PERMISSIONS),
    }

    snapshot.assert_match(
        json.dumps(actual, indent=2, sort_keys=True) + "\n",
        "permission_catalogs.json",
    )
