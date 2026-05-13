from __future__ import annotations

import pytest

pytestmark = pytest.mark.api

AUTH = {"Authorization": "Bearer test-token"}
START = "2026-01-01T00:00:00Z"
END = "2026-01-01T01:00:00Z"


@pytest.mark.asyncio
async def test_logging_query_routes_parse_filters_and_delegate(api_client, authenticated_api) -> None:
    simple = await api_client.get(
        "/v1/logging/",
        headers=AUTH,
        params={
            "start": START,
            "end": END,
            "limit": 25,
            "direction": "forward",
            "level": "info",
            "keyword": "created",
            "filters": "project:demo,route:chat",
            "custom_query": "{app=\"gantry\"}",
        },
    )
    complex_query = await api_client.post(
        "/v1/logging/",
        headers=AUTH,
        json={
            "start": START,
            "end": END,
            "limit": 10,
            "direction": "backward",
            "level": "error",
            "keyword": "failed",
            "filters": {"project": "demo"},
            "custom_query": None,
        },
    )

    assert simple.status_code == 200
    assert simple.json()[0]["message"] == "ok"
    assert complex_query.status_code == 200
    simple_call = authenticated_api["logging"].calls[-2][1]
    complex_call = authenticated_api["logging"].calls[-1][1]
    assert simple_call[0] == "org-1"
    assert simple_call[4] == 25
    assert simple_call[8] == {"project": "demo", "route": "chat"}
    assert complex_call[4] == 10
    assert complex_call[8] == {"project": "demo"}


@pytest.mark.asyncio
async def test_logging_query_validation_rejects_bad_direction(api_client, authenticated_api) -> None:
    response = await api_client.get(
        "/v1/logging/",
        headers=AUTH,
        params={"start": START, "end": END, "direction": "sideways"},
    )

    assert response.status_code in {400, 422}
