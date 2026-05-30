from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.automation, pytest.mark.smoke]


WORKFLOW_FILES = {
    "unit": "unit-test.yml",
    "api": "api-test.yml",
    "integration": "integration-test.yml",
    "regression": "regression-test.yml",
    "e2e": "e2e-test.yml",
    "performance": "performance-test.yml",
    "automation": "automation-test.yml",
}


def _workflow(repo_root, name: str) -> str:
    return (repo_root / ".github" / "workflows" / name).read_text()


def _workflow_path(repo_root, name: str) -> Path:
    return repo_root / ".github" / "workflows" / name


def _make_target_body(makefile: str, target: str) -> str:
    pattern = rf"^{re.escape(target)}:\n(?P<body>(?:\t.*\n|[ \t]*\n)*)"
    match = re.search(pattern, makefile, flags=re.MULTILINE)
    assert match, f"Missing Makefile target {target}"
    return match.group("body")


def test_makefile_exposes_all_layered_test_targets(repo_root) -> None:
    makefile = (repo_root / "Makefile").read_text()
    required_targets = {
        "test-unit",
        "test-api",
        "test-integration",
        "test-regression",
        "test-perf",
        "test-e2e",
        "test-automation",
        "test-ci-fast",
        "test-ci-full",
        "test-all",
    }
    actual_targets = set(re.findall(r"^([a-zA-Z0-9_-]+):", makefile, flags=re.MULTILINE))

    assert required_targets <= actual_targets


def test_makefile_enforces_api_coverage_gate_and_reports(repo_root) -> None:
    makefile = (repo_root / "Makefile").read_text()

    assert "COVERAGE_FAIL_UNDER ?= 80" in makefile
    assert "test-api:" in makefile
    assert "$(PYTEST_XDIST)" in makefile
    assert "--cov-report=xml:reports/api/coverage.xml" in makefile
    assert "--junitxml=reports/api/junit.xml" in makefile
    assert "--cov-fail-under=$(COVERAGE_FAIL_UNDER)" in makefile


def test_automation_target_is_smoke_policy_not_full_suite(repo_root) -> None:
    makefile = (repo_root / "Makefile").read_text()

    assert "tests/automation -m \"automation or smoke\"" in makefile
    assert "--alluredir=reports/allure" in makefile
    assert "--cov-report=xml:reports/automation/coverage.xml" in makefile
    assert "AUTOMATION_COVERAGE_FAIL_UNDER ?= 0" in makefile


@pytest.mark.parametrize("target", ["test-api", "test-regression", "test-automation", "test-perf"])
def test_fast_or_no_docker_targets_do_not_start_external_services(repo_root, target: str) -> None:
    makefile = (repo_root / "Makefile").read_text()
    body = _make_target_body(makefile, target)

    assert "docker compose" not in body
    assert "testcontainers" not in body.lower()
    assert "make test-integration" not in body
    assert "make test-e2e" not in body


def test_regression_fuzz_installs_fakes_before_calling_generated_cases(repo_root) -> None:
    fuzz_test = (repo_root / "tests/regression/test_openapi_fuzz.py").read_text()

    assert "_install_fake_dependencies" in fuzz_test
    assert "respx.mock" in fuzz_test
    assert "localhost:6379" not in fuzz_test
    assert "localhost:5432" not in fuzz_test


@pytest.mark.parametrize("name", ["unit", "api", "regression", "automation"])
def test_fast_pr_gate_workflows_target_dev(repo_root, name: str) -> None:
    content = _workflow(repo_root, WORKFLOW_FILES[name])

    assert "pull_request:" in content
    assert "branches: [dev]" in content
    assert "workflow_dispatch:" in content


def test_integration_workflow_is_path_filtered_dev_pr_gate(repo_root) -> None:
    content = _workflow(repo_root, WORKFLOW_FILES["integration"])

    assert "pull_request:" in content
    assert "branches: [dev]" in content
    for path in [
        "main-db-migrations/**",
        "src/gantry/db/**",
        "src/gantry/keycloak/**",
        "src/gantry/management/**",
        "asset/gantry-realm.json",
        "tests/integration/**",
    ]:
        assert path in content


def test_slow_workflows_are_not_pr_gates(repo_root) -> None:
    for name in [WORKFLOW_FILES["e2e"], WORKFLOW_FILES["performance"]]:
        content = _workflow(repo_root, name)
        assert "pull_request:" not in content
        assert "workflow_dispatch:" in content


def test_performance_workflow_keeps_load_smoke_manual_only(repo_root) -> None:
    content = _workflow(repo_root, WORKFLOW_FILES["performance"])

    assert "benchmark:" in content
    assert "load-smoke:" in content
    assert "inputs.run_load_smoke == 'true'" in content


@pytest.mark.parametrize("name", WORKFLOW_FILES.values())
def test_workflows_have_timeout_and_concurrency(repo_root, name: str) -> None:
    content = _workflow(repo_root, name)

    assert "concurrency:" in content
    assert "cancel-in-progress: true" in content
    assert "timeout-minutes:" in content


@pytest.mark.parametrize(
    ("name", "target"),
    [
        ("unit-test.yml", "make test-unit"),
        ("api-test.yml", "make test-api"),
        ("integration-test.yml", "make test-integration"),
        ("regression-test.yml", "make test-regression"),
        ("e2e-test.yml", "make test-e2e-backend"),
        ("performance-test.yml", "make test-perf"),
        ("automation-test.yml", "make test-automation"),
    ],
)
def test_workflows_call_expected_make_targets(repo_root, name: str, target: str) -> None:
    content = _workflow(repo_root, name)

    assert target in content


@pytest.mark.parametrize("name", WORKFLOW_FILES.values())
def test_test_workflows_do_not_upload_artifacts_on_free_ci(repo_root, name: str) -> None:
    content = _workflow(repo_root, name)

    assert "actions/upload-artifact" not in content
    assert "Upload " not in content


def test_api_workflow_runs_behavior_contract_suite(repo_root) -> None:
    content = _workflow(repo_root, "api-test.yml")

    assert "make test-api" in content
    assert (repo_root / "tests/api/test_all_route_security_and_validation.py").exists()
    assert (repo_root / "tests/api/test_domain_error_contracts.py").exists()


def test_workflow_files_are_tracked_as_yaml(repo_root) -> None:
    for name in WORKFLOW_FILES.values():
        assert _workflow_path(repo_root, name).suffix == ".yml"


def test_legacy_e2e_folder_is_not_reintroduced(repo_root) -> None:
    assert not (repo_root / "e2e_test").exists()
