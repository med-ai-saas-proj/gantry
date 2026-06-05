from __future__ import annotations

import tomllib

import pytest

from tests.api.coverage_matrix import EXPECTED_OPERATION_COUNTS
from tests.helpers.routes import operations

pytestmark = [pytest.mark.automation, pytest.mark.smoke]


def test_management_app_has_openapi_schema(management_openapi: dict) -> None:
    assert management_openapi["info"]["title"]
    assert management_openapi["paths"]


@pytest.mark.parametrize(
    "fixture_name",
    [
        "management_openapi",
        "service_openapi",
        "gateway_openapi",
        "internal_openapi",
    ],
)
def test_all_fastapi_apps_have_openapi_schema(request, fixture_name: str) -> None:
    openapi = request.getfixturevalue(fixture_name)

    assert openapi["openapi"]
    assert openapi["info"]["title"]
    assert openapi["paths"]


def test_smoke_public_management_routes_are_registered(management_paths: dict) -> None:
    assert "/v1/organizations/permissions" in management_paths
    assert "/v1/projects/permissions" in management_paths


@pytest.mark.parametrize(
    ("app_name", "fixture_name"),
    [
        ("management", "management_openapi"),
        ("service", "service_openapi"),
        ("gateway", "gateway_openapi"),
        ("internal", "internal_openapi"),
    ],
)
def test_openapi_operation_counts_match_api_coverage_matrix(
    request,
    app_name: str,
    fixture_name: str,
) -> None:
    openapi = request.getfixturevalue(fixture_name)

    assert len(operations(openapi)) == EXPECTED_OPERATION_COUNTS[app_name]


def test_example_config_parses_and_contains_required_sections(repo_root) -> None:
    config = tomllib.loads((repo_root / "example.gantry.toml").read_text())

    assert config["stage"] == "DEV"
    assert {"db", "apikey", "keycloak", "auth", "organization"} <= set(config)
    assert len(config["apikey"]["secret"]) > 16
    assert config["keycloak"]["realm_name"] == "gantry"


def test_ci_suite_workflows_are_present(repo_root) -> None:
    workflow_dir = repo_root / ".github" / "workflows"
    expected = {
        "unit-test.yml",
        "api-test.yml",
        "integration-test.yml",
        "regression-test.yml",
        "e2e-test.yml",
        "performance-test.yml",
        "automation-test.yml",
    }

    assert expected <= {path.name for path in workflow_dir.glob("*.yml")}
