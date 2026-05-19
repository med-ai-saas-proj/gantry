from __future__ import annotations

import pytest

from gantry.management.organization.permissions import (
    OrgPermission,
    get_effective_permissions as get_effective_org_permissions,
)
from gantry.management.project.permissions import (
    ProjectPermission,
    get_effective_permissions as get_effective_project_permissions,
)
from gantry.shared.utils.uuid_utils import uuid7

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
