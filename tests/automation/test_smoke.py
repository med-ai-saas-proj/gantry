from __future__ import annotations

import tomllib

import pytest
from fastapi.testclient import TestClient

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


@pytest.mark.parametrize(
    ("app_fixture", "path"),
    [
        ("main_app", "/health"),
        ("main_app", "/ready"),
        ("management_app", "/health"),
        ("management_app", "/ready"),
        ("service_app", "/health"),
        ("service_app", "/ready"),
        ("gateway_app", "/health"),
        ("gateway_app", "/ready"),
        ("internal_app", "/health"),
        ("internal_app", "/ready"),
    ],
)
def test_all_runtime_apps_expose_public_health_endpoints(
    request,
    app_fixture: str,
    path: str,
) -> None:
    app = request.getfixturevalue(app_fixture)

    response = TestClient(app).get(path)

    assert response.status_code == 200


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
