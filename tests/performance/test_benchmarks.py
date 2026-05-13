from __future__ import annotations

import pytest

from gantry.shared.utils.permission_utils import serialize_project_permission_values

pytestmark = [pytest.mark.performance, pytest.mark.timeout(30)]


def test_project_permission_serialization_baseline_latency(benchmark) -> None:
    permissions = {
        f"project-{index}": [
            "project.read",
            "project.settings.read",
            "apikey.read",
        ]
        for index in range(100)
    }

    result = benchmark(serialize_project_permission_values, permissions)

    assert len(result) == 100
