from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tests.helpers.routes import HTTP_METHODS, operations

EXPECTED_OPERATION_COUNTS = {
    "management": 92,
    "service": 34,
    "gateway": 10,
    "internal": 9,
}

APP_GROUPS = {
    "management": {
        "admin": ("/v1/admin",),
        "api_key": ("/v1/api-keys",),
        "billing": ("/v1/billing",),
        "logging": ("/v1/logging",),
        "organization": ("/v1/organizations",),
        "project": ("/v1/projects",),
    },
    "service": {
        "conversation": ("/v1/conversations",),
        "file_storage": ("/v1/file-storage",),
        "rag": ("/v1/rag",),
    },
    "gateway": {
        "gateway": ("/",),
    },
    "internal": {
        "internal_billing": ("/billing",),
    },
}

PUBLIC_OPERATIONS = {
    ("management", "GET", "/v1/organizations/permissions"),
    ("management", "GET", "/v1/projects/permissions"),
    ("management", "POST", "/v1/billing/webhook/stripe"),
}


@dataclass(frozen=True)
class OperationCoverage:
    app_name: str
    method: str
    path: str
    group: str
    scenarios: frozenset[str]


def _operation_spec(openapi: dict[str, Any], method: str, path: str) -> dict[str, Any]:
    return openapi["paths"][path][method.lower()]


def _operation_group(app_name: str, path: str) -> str:
    for group, prefixes in APP_GROUPS[app_name].items():
        if any(path.startswith(prefix) for prefix in prefixes):
            return group
    raise AssertionError(f"{app_name}:{path} has no API test group")


def _has_query_or_path_params(spec: dict[str, Any]) -> bool:
    return bool(spec.get("parameters"))


def _has_request_body(spec: dict[str, Any]) -> bool:
    return "requestBody" in spec


def _is_list_or_search(method: str, path: str, spec: dict[str, Any]) -> bool:
    if method != "GET":
        return False
    if any(name in path for name in ("/users", "/projects", "/api-keys", "/invoices", "/transactions", "/files", "/messages")):
        return True
    return any(
        parameter.get("name") in {"limit", "offset", "q", "query", "period", "paid"}
        for parameter in spec.get("parameters", [])
    )


def required_scenarios(
    app_name: str,
    method: str,
    path: str,
    spec: dict[str, Any],
) -> frozenset[str]:
    scenarios = {"happy_path"}
    if (app_name, method, path) not in PUBLIC_OPERATIONS:
        scenarios.add("missing_auth")
    if _has_query_or_path_params(spec):
        scenarios.add("invalid_path_or_query")
    if _has_request_body(spec):
        scenarios.add("invalid_body")
    if method in {"GET", "PUT", "PATCH", "DELETE", "POST"} and "{" in path:
        scenarios.add("not_found_or_denied")
    if _is_list_or_search(method, path, spec):
        scenarios.add("pagination_or_filter")
    return frozenset(scenarios)


def coverage_matrix(app_name: str, openapi: dict[str, Any]) -> list[OperationCoverage]:
    return [
        OperationCoverage(
            app_name=app_name,
            method=method,
            path=path,
            group=_operation_group(app_name, path),
            scenarios=required_scenarios(
                app_name,
                method,
                path,
                _operation_spec(openapi, method, path),
            ),
        )
        for method, path in operations(openapi)
    ]


def assert_operation_count_is_current(app_name: str, openapi: dict[str, Any]) -> None:
    actual = len(operations(openapi))
    expected = EXPECTED_OPERATION_COUNTS[app_name]
    assert actual == expected, (
        f"{app_name} OpenAPI operation count changed from {expected} to {actual}. "
        "Update API tests and coverage_matrix.py intentionally."
    )


def assert_matrix_is_complete(app_name: str, openapi: dict[str, Any]) -> None:
    assert_operation_count_is_current(app_name, openapi)
    missing: list[str] = []
    for coverage in coverage_matrix(app_name, openapi):
        if not coverage.group:
            missing.append(f"{coverage.method} {coverage.path}: group")
        if "happy_path" not in coverage.scenarios:
            missing.append(f"{coverage.method} {coverage.path}: happy_path")
        if not coverage.scenarios:
            missing.append(f"{coverage.method} {coverage.path}: scenarios")
    assert not missing, "missing API coverage metadata: " + ", ".join(missing)


def operations_with_request_body(openapi: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (method, path)
        for method, path in operations(openapi)
        if _has_request_body(_operation_spec(openapi, method, path))
    ]


def protected_operations(app_name: str, openapi: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (method, path)
        for method, path in operations(openapi)
        if (app_name, method, path) not in PUBLIC_OPERATIONS
    ]


def list_or_filter_operations(openapi: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (method, path)
        for method, path in operations(openapi)
        if _is_list_or_search(method, path, _operation_spec(openapi, method, path))
    ]
