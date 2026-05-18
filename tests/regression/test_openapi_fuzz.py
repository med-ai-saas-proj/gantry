from __future__ import annotations

import pytest
import schemathesis
from hypothesis import HealthCheck, given, settings

from tests.regression.helpers import assert_no_unexpected_5xx

pytestmark = pytest.mark.regression


SAFE_OPERATIONS = {
    "management": [
        ("GET", "/v1/organizations/permissions"),
        ("GET", "/v1/projects/permissions"),
        ("GET", "/v1/api-keys/permissions"),
        ("GET", "/v1/admin/dashboard/summary"),
        ("GET", "/v1/billing/transactions"),
    ],
    "service": [
        ("GET", "/v1/conversations/{conversation_uid}"),
        ("GET", "/v1/conversations/{conversation_uid}/messages"),
        ("GET", "/v1/file-storage/service/"),
        ("GET", "/v1/file-storage/user/"),
        ("GET", "/v1/rag/service/files"),
        ("GET", "/v1/rag/user/files"),
    ],
    "gateway": [
        ("GET", "/{route_name}"),
        ("GET", "/{route_name}/{full_path}"),
    ],
    "internal": [
        ("GET", "/billing/credits/{org_id}/available"),
        ("GET", "/billing/credits/{org_id}/transactions"),
        ("GET", "/billing/invoices"),
        ("GET", "/billing/invoices/{invoice_uid}"),
    ],
}


def _schema_for(app_name: str, request):
    app = request.getfixturevalue(f"{app_name}_app")
    openapi = request.getfixturevalue(f"{app_name}_openapi")
    schema = schemathesis.openapi.from_dict(openapi)
    schema.app = app
    return schema


def _operation(schema, method: str, path: str):
    return next(
        result.ok()
        for result in schema.get_all_operations()
        if result.ok().path == path and result.ok().method == method.lower()
    )


def _auth_headers(app_name: str) -> dict[str, str]:
    headers = {
        "Authorization": "Bearer regression-token",
        "X-Api-Key": "sk_regression",
        "stripe-signature": "invalid",
    }
    if app_name == "gateway":
        return {"X-Api-Key": "sk_regression"}
    return headers


@pytest.mark.order(3)
@pytest.mark.parametrize(
    ("app_name", "method", "path"),
    [
        (app_name, method, path)
        for app_name, operations in SAFE_OPERATIONS.items()
        for method, path in operations
    ],
)
def test_schemathesis_generates_safe_read_cases_for_all_apps(
    request,
    app_name: str,
    method: str,
    path: str,
) -> None:
    schema = _schema_for(app_name, request)
    operation = _operation(schema, method, path)
    case = operation.as_strategy().example()

    assert case.method == method
    assert case.path == path


@pytest.mark.order(3)
@pytest.mark.parametrize(
    ("app_name", "method", "path"),
    [
        (app_name, method, path)
        for app_name, operations in SAFE_OPERATIONS.items()
        for method, path in operations
    ],
)
def test_schemathesis_safe_read_cases_do_not_return_unexpected_5xx(
    request,
    app_name: str,
    method: str,
    path: str,
) -> None:
    schema = _schema_for(app_name, request)
    operation = _operation(schema, method, path)
    case = operation.as_strategy().example()
    response = case.call(
        base_url="http://testserver",
        headers=_auth_headers(app_name),
    )

    assert_no_unexpected_5xx(response)


@pytest.mark.order(3)
def test_schemathesis_fuzzes_management_permission_catalog_without_5xx(request) -> None:
    schema = _schema_for("management", request)
    operation = _operation(schema, "GET", "/v1/organizations/permissions")

    @given(case=operation.as_strategy())
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def _run(case) -> None:
        response = case.call(base_url="http://testserver")
        assert_no_unexpected_5xx(response)

    _run()
