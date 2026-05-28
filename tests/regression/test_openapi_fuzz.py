from __future__ import annotations

import pytest
import schemathesis
from hypothesis import HealthCheck, given, settings

from tests.regression.helpers import assert_no_unexpected_5xx

pytestmark = pytest.mark.regression

FUZZ_SAMPLE_LIMIT = 8


def _schema_for(app_name: str, request):
    app = request.getfixturevalue(f"{app_name}_app")
    openapi = request.getfixturevalue(f"{app_name}_openapi")
    schema = schemathesis.openapi.from_dict(openapi)
    schema.app = app
    return schema


def _safe_read_operations(schema, limit: int | None = FUZZ_SAMPLE_LIMIT):
    operations = [
        operation
        for result in schema.get_all_operations()
        if (operation := result.ok()).method == "get"
    ]
    if limit is None:
        return operations
    return operations[:limit]


def _auth_headers(app_name: str) -> dict[str, str]:
    headers = {
        "Authorization": "Bearer regression-token",
        "X-Api-Key": "sk_regression",
        "stripe-signature": "invalid",
    }
    if app_name == "gateway":
        return {"X-Api-Key": "sk_regression"}
    return headers


def _call_case_asserting_no_unexpected_5xx(case, **kwargs) -> None:
    try:
        response = case.call(**kwargs)
    except Exception as exc:
        status = getattr(exc, "status", None)
        if isinstance(status, int) and status < 500:
            return
        raise
    assert_no_unexpected_5xx(response)


@pytest.mark.order(3)
@pytest.mark.parametrize(
    "app_name",
    ["management", "service", "gateway", "internal"],
)
def test_schemathesis_safe_read_cases_do_not_return_unexpected_5xx(
    request,
    app_name: str,
) -> None:
    schema = _schema_for(app_name, request)
    for operation in _safe_read_operations(schema):
        case = operation.as_strategy().example()
        _call_case_asserting_no_unexpected_5xx(
            case,
            base_url="http://testserver",
            headers=_auth_headers(app_name),
        )


@pytest.mark.order(3)
def test_schemathesis_fuzzes_public_management_read_without_5xx(request) -> None:
    schema = _schema_for("management", request)
    operation = next(
        operation
        for operation in _safe_read_operations(schema, limit=None)
        if "security" not in operation.definition.raw
    )

    @given(case=operation.as_strategy())
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def _run(case) -> None:
        _call_case_asserting_no_unexpected_5xx(
            case,
            base_url="http://testserver",
        )

    _run()
