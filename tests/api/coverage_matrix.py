from __future__ import annotations

from typing import Any

from tests.helpers.routes import operations


def _operation_spec(openapi: dict[str, Any], method: str, path: str) -> dict[str, Any]:
    return openapi["paths"][path][method.lower()]


def _has_request_body(spec: dict[str, Any]) -> bool:
    return "requestBody" in spec


def operations_with_request_body(openapi: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (method, path)
        for method, path in operations(openapi)
        if _has_request_body(_operation_spec(openapi, method, path))
    ]


def operations_requiring_security(openapi: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (method, path)
        for method, path in operations(openapi)
        if _operation_spec(openapi, method, path).get("security")
    ]
