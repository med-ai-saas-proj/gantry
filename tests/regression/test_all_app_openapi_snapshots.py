from __future__ import annotations

import pytest

from tests.helpers.routes import operation_lines

pytestmark = pytest.mark.regression


@pytest.mark.order(1)
@pytest.mark.parametrize(
    ("openapi_fixture", "snapshot_name"),
    [
        ("management_openapi", "management_operations.tsv"),
        ("service_openapi", "service_operations.tsv"),
        ("gateway_openapi", "gateway_operations.tsv"),
        ("internal_openapi", "internal_operations.tsv"),
    ],
)
def test_app_operations_match_snapshot(
    request,
    repo_root,
    openapi_fixture: str,
    snapshot_name: str,
) -> None:
    openapi = request.getfixturevalue(openapi_fixture)
    expected = (repo_root / "tests" / "snapshots" / snapshot_name).read_text()
    assert "\n".join(operation_lines(openapi)) + "\n" == expected


def test_service_and_internal_canonical_user_story_paths_remain_present(
    service_paths: dict,
    internal_paths: dict,
    gateway_paths: dict,
) -> None:
    for path in [
        "/v1/conversations/",
        "/v1/file-storage/service/",
        "/v1/file-storage/user/",
        "/v1/rag/service/files",
        "/v1/rag/user/files",
    ]:
        assert path in service_paths

    for path in ["/billing/", "/billing/credits", "/billing/invoices"]:
        assert path in internal_paths

    assert "/{route_name}/{full_path}" in gateway_paths
