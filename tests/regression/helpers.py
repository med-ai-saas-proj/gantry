from __future__ import annotations

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
