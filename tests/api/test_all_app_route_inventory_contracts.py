from __future__ import annotations

import pytest

from tests.api.coverage_matrix import (
    assert_matrix_is_complete,
    coverage_matrix,
    list_or_filter_operations,
    operations_with_request_body,
)
from tests.helpers.routes import assert_operation_grouped, operations

pytestmark = pytest.mark.api


def test_every_management_operation_is_assigned_to_a_contract_group(management_openapi: dict) -> None:
    assert_matrix_is_complete("management", management_openapi)
    assert_operation_grouped(
        "management",
        management_openapi,
        {
            "admin": ["/v1/admin"],
            "api_key": ["/v1/api-keys"],
            "billing": ["/v1/billing"],
            "logging": ["/v1/logging"],
            "organization": ["/v1/organizations"],
            "project": ["/v1/projects"],
        },
    )


def test_every_service_operation_is_assigned_to_a_contract_group(service_openapi: dict) -> None:
    assert_matrix_is_complete("service", service_openapi)
    assert_operation_grouped(
        "service",
        service_openapi,
        {
            "conversation": ["/v1/conversations"],
            "file_storage": ["/v1/file-storage"],
            "rag": ["/v1/rag"],
        },
    )


def test_every_internal_operation_is_assigned_to_a_contract_group(internal_openapi: dict) -> None:
    assert_matrix_is_complete("internal", internal_openapi)
    assert_operation_grouped(
        "internal",
        internal_openapi,
        {"internal_billing": ["/billing"]},
    )


def test_gateway_proxy_operations_are_registered(gateway_openapi: dict) -> None:
    assert_matrix_is_complete("gateway", gateway_openapi)
    assert sorted(operations(gateway_openapi)) == [
        ("DELETE", "/{route_name}"),
        ("DELETE", "/{route_name}/{full_path}"),
        ("GET", "/{route_name}"),
        ("GET", "/{route_name}/{full_path}"),
        ("PATCH", "/{route_name}"),
        ("PATCH", "/{route_name}/{full_path}"),
        ("POST", "/{route_name}"),
        ("POST", "/{route_name}/{full_path}"),
        ("PUT", "/{route_name}"),
        ("PUT", "/{route_name}/{full_path}"),
    ]


@pytest.mark.parametrize(
    ("app_name", "fixture_name"),
    [
        ("management", "management_openapi"),
        ("service", "service_openapi"),
        ("gateway", "gateway_openapi"),
        ("internal", "internal_openapi"),
    ],
)
def test_api_coverage_matrix_records_required_scenario_classes(
    request,
    app_name: str,
    fixture_name: str,
) -> None:
    openapi = request.getfixturevalue(fixture_name)
    matrix = coverage_matrix(app_name, openapi)

    assert matrix
    assert all("happy_path" in item.scenarios for item in matrix)
    assert any("missing_auth" in item.scenarios for item in matrix)
    assert all(item.group for item in matrix)


@pytest.mark.parametrize(
    "fixture_name",
    ["management_openapi", "service_openapi", "internal_openapi"],
)
def test_request_body_operations_are_marked_for_invalid_body_contract(
    request,
    fixture_name: str,
) -> None:
    openapi = request.getfixturevalue(fixture_name)
    body_operations = set(operations_with_request_body(openapi))
    matrix = coverage_matrix(fixture_name.removesuffix("_openapi"), openapi)

    missing = [
        f"{item.method} {item.path}"
        for item in matrix
        if (item.method, item.path) in body_operations
        and "invalid_body" not in item.scenarios
    ]
    assert not missing


@pytest.mark.parametrize(
    "fixture_name",
    ["management_openapi", "service_openapi", "internal_openapi"],
)
def test_list_operations_are_marked_for_pagination_or_filter_contract(
    request,
    fixture_name: str,
) -> None:
    openapi = request.getfixturevalue(fixture_name)
    list_operations = set(list_or_filter_operations(openapi))
    matrix = coverage_matrix(fixture_name.removesuffix("_openapi"), openapi)

    missing = [
        f"{item.method} {item.path}"
        for item in matrix
        if (item.method, item.path) in list_operations
        and "pagination_or_filter" not in item.scenarios
    ]
    assert not missing
