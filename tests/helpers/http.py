from __future__ import annotations

from typing import Any


def assert_no_5xx(response) -> None:
    assert response.status_code < 500, response.text


def assert_error_response(response, expected_status: int | set[int]) -> dict[str, Any]:
    if isinstance(expected_status, int):
        expected_status = {expected_status}
    assert response.status_code in expected_status, response.text
    assert_no_5xx(response)
    payload = response.json()
    assert isinstance(payload, dict)
    assert "status" in payload or "detail" in payload or "errors" in payload
    return payload


def assert_json_object(response) -> dict[str, Any]:
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


def assert_keys(payload: dict[str, Any], expected: set[str]) -> None:
    missing = expected - set(payload)
    assert not missing, f"missing keys: {sorted(missing)}"


def assert_paginated(payload: dict[str, Any]) -> list[dict[str, Any]]:
    assert_keys(payload, {"total", "results"})
    assert isinstance(payload["total"], int)
    assert isinstance(payload["results"], list)
    return payload["results"]

