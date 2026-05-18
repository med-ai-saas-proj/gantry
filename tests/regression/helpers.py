from __future__ import annotations

from typing import Any

from tests.helpers.routes import HTTP_METHODS


VOLATILE_SCHEMA_KEYS = {"example", "examples"}


def normalize_schema(value: Any) -> Any:
    """Return a deterministic OpenAPI schema snapshot payload."""
    if isinstance(value, dict):
        return {
            key: normalize_schema(item)
            for key, item in sorted(value.items())
            if key not in VOLATILE_SCHEMA_KEYS
        }
    if isinstance(value, list):
        return [normalize_schema(item) for item in value]
    return value


def operation_contracts(openapi: dict) -> dict:
    contracts = {}
    for path, methods in sorted(openapi["paths"].items()):
        for method, operation in sorted(methods.items()):
            if method not in HTTP_METHODS:
                continue
            operation_id = operation.get("operationId")
            if (
                isinstance(operation_id, str)
                and operation_id.startswith("gateway_proxy__route_name")
            ):
                operation_id = "gateway_proxy"
            contracts[f"{method.upper()} {path}"] = {
                "operationId": operation_id,
                "parameters": normalize_schema(
                    [
                        {
                            "name": parameter.get("name"),
                            "in": parameter.get("in"),
                            "required": parameter.get("required", False),
                            "schema": parameter.get("schema", {}),
                        }
                        for parameter in operation.get("parameters", [])
                    ]
                ),
                "requestBody": bool(operation.get("requestBody")),
                "responses": sorted(operation.get("responses", {}).keys()),
                "security": operation.get("security", []),
            }
    return contracts


def selected_schemas(openapi: dict, names: list[str]) -> dict:
    schemas = openapi.get("components", {}).get("schemas", {})
    missing = [name for name in names if name not in schemas]
    if missing:
        raise AssertionError(f"Missing OpenAPI schemas: {missing}")
    return {name: normalize_schema(schemas[name]) for name in names}


def schema_properties(openapi: dict, schema_name: str) -> set[str]:
    return set(
        openapi.get("components", {})
        .get("schemas", {})
        .get(schema_name, {})
        .get("properties", {})
    )


def assert_no_unexpected_5xx(response) -> None:
    status_code = getattr(response, "status_code", None)
    assert status_code is not None
    assert status_code < 500, getattr(response, "text", "")
