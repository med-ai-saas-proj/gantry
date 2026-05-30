from __future__ import annotations

import pytest

from gantry.management.admin.dtos import AdminUserProjectPermissionUpdateRequest
from gantry.management.admin.permissions import (
    build_permission_summary,
    flatten_project_permission_updates,
)
from gantry.management.organization.permissions import (
    OrgPermission,
    get_effective_permissions as get_effective_org_permissions,
)
from gantry.management.project.permissions import (
    ProjectPermission,
    get_effective_permissions as get_effective_project_permissions,
)
from gantry.shared.utils.uuid_utils import uuid7
from tests.performance.helpers import admin_permission_attributes

pytestmark = [pytest.mark.performance, pytest.mark.timeout(30)]


def test_permission_hierarchy_expansion_latency(benchmark) -> None:
    def expand_all() -> tuple[set[str], set[str]]:
        return (
            get_effective_org_permissions([OrgPermission.OWNER.value]),
            get_effective_project_permissions([ProjectPermission.OWNER.value]),
        )

    org_permissions, project_permissions = benchmark(expand_all)

    assert OrgPermission.USERS_PERMISSIONS_RW.value in org_permissions
    assert ProjectPermission.APIKEY_WRITE.value in project_permissions


def test_uuid7_generation_latency(benchmark) -> None:
    generated = benchmark(lambda: [uuid7() for _ in range(100)])

    assert len(generated) == 100
    assert len({str(value) for value in generated}) == 100


def test_admin_permission_summary_build_and_flatten_latency(benchmark) -> None:
    attrs = admin_permission_attributes(100)

    def build_and_flatten() -> tuple[int, dict[str, list[str]]]:
        summary = build_permission_summary(attrs)
        flattened = flatten_project_permission_updates(
            [
                AdminUserProjectPermissionUpdateRequest(
                    project_uuid=item.project_uuid,
                    permissions=item.permissions,
                )
                for item in summary.project_permissions
            ]
        )
        return len(summary.project_permissions), flattened

    project_count, flattened = benchmark(build_and_flatten)

    assert project_count == 100
    assert flattened["project-0"] == [
        "apikey.read",
        "project.read",
        "project.settings.read",
    ]
