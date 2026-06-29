from __future__ import annotations

from gantry.api_gateway.routes import (
    filter_headers,
    _inject_api_key_context_headers,
    _to_url_string,
)

import json

from pydantic import AnyUrl


def _api_key_info_payload() -> dict:
    return {
        "api_key_id": 10,
        "api_key_uuid": "api-key-1",
        "project_id": 20,
        "project_uuid": "11111111-1111-1111-1111-111111111111",
        "org_id": "org-1",
        "organization_uuid": "org-1",
        "user_uuid": "user-1",
        "hashed_key": "hashed",
        "permissions": ["conversation.read"],
        "rpm_limit_organization": 1000,
        "rpm_limit_project": 500,
        "spending_limit_organization": 100000,
        "spending_limit_project": 50000,
    }


def test_filter_headers_removes_hop_by_hop_headers_case_insensitively() -> None:
    filtered = filter_headers(
        {
            "Connection": "keep-alive",
            "Content-Length": "10",
            "X-Keep": "yes",
            "host": "example.test",
        }
    )

    assert filtered == {"X-Keep": "yes"}


def test_to_url_string_accepts_plain_string_and_pydantic_url() -> None:
    assert _to_url_string("https://upstream.example/base/") == (
        "https://upstream.example/base/"
    )
    assert _to_url_string(AnyUrl("https://upstream.example/base/")) == (
        "https://upstream.example/base/"
    )


def test_inject_api_key_context_headers_uses_public_header_names() -> None:
    headers = _inject_api_key_context_headers(_api_key_info_payload())

    assert headers["X-Organization-UUID"] == "org-1"
    assert headers["X-Project-UUID"] == "11111111-1111-1111-1111-111111111111"
    assert headers["X-API-Key-UUID"] == "api-key-1"
    assert json.loads(headers["X-Permissions"])[0] == "conversation.read"
    assert headers["X-RPM-Limit-Organization"] == "1000"
    assert headers["X-Spending-Limit-Project"] == "50000"
