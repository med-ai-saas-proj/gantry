from __future__ import annotations

import pytest

pytestmark = pytest.mark.api


@pytest.mark.asyncio
async def test_openapi_json_status_and_schema(api_client) -> None:
    response = await api_client.get("/docs/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["openapi"].startswith("3.")
    assert "paths" in payload
    assert "components" in payload


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
