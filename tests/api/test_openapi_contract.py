from __future__ import annotations

import pytest

from tests.helpers.http import assert_openapi_operation

pytestmark = pytest.mark.api


@pytest.mark.asyncio
async def test_openapi_json_status_and_schema(api_client) -> None:
    response = await api_client.get("/docs/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["openapi"].startswith("3.")
    assert "paths" in payload
    assert "components" in payload


@pytest.mark.parametrize(("path", "method"), [
    ("/v1/organizations/permissions", "get"),
    ("/v1/projects/permissions", "get"),
    ("/v1/api-keys/permissions", "get"),
    ("/v1/api-keys/{api_key_uuid}", "get"),
    ("/v1/admin/dashboard/summary", "get"),
    ("/v1/admin/users", "get"),
])
def test_expected_management_operations_are_registered(
    management_paths: dict, path: str, method: str
) -> None:
    operation = assert_openapi_operation(management_paths, path, method)

    assert "responses" in operation


def test_all_management_operations_define_success_responses(
    management_openapi: dict,
) -> None:
    for path, methods in management_openapi["paths"].items():
        for method, operation in methods.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            responses = operation["responses"]
            assert any(code.startswith("2") for code in responses), (
                f"{method.upper()} {path} has no 2xx response"
            )
            if any(
                parameter.get("in") in {"path", "query"}
                for parameter in operation.get("parameters", [])
            ) or "requestBody" in operation:
                assert "422" in responses, (
                    f"{method.upper()} {path} has no validation response"
                )


@pytest.mark.parametrize(
    "fixture_name",
    ["service_openapi", "gateway_openapi", "internal_openapi"],
)
def test_non_management_operations_define_success_responses(
    request,
    fixture_name: str,
) -> None:
    openapi = request.getfixturevalue(fixture_name)
    for path, methods in openapi["paths"].items():
        for method, operation in methods.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            responses = operation["responses"]
            assert any(code.startswith("2") for code in responses), (
                f"{method.upper()} {path} has no 2xx response"
            )


def test_non_public_management_operations_define_security(
    management_openapi: dict,
) -> None:
    public_operations = {
        ("GET", "/v1/organizations/permissions"),
        ("GET", "/v1/projects/permissions"),
        ("POST", "/v1/billing/webhook/stripe"),
    }

    for path, methods in management_openapi["paths"].items():
        for method, operation in methods.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            key = (method.upper(), path)
            if key in public_operations:
                continue
            assert operation.get("security"), (
                f"{method.upper()} {path} is missing security metadata"
            )
