from __future__ import annotations

import json

import httpx
import pytest
import respx

pytestmark = pytest.mark.api


def _json_response() -> httpx.Response:
    return httpx.Response(
        202,
        json={"ok": True},
        headers={"Content-Type": "application/json", "Connection": "close", "X-Upstream": "kept"},
    )


@pytest.mark.asyncio
async def test_gateway_proxy_forwards_request_and_injects_api_key_context_headers(
    gateway_client,
    authenticated_gateway_api,
) -> None:
    upstream_url = "https://upstream.example/base/v1/messages"
    with respx.mock(assert_all_called=True) as router:
        route = router.post(upstream_url).mock(return_value=_json_response())
        response = await gateway_client.post(
            "/chat/v1/messages",
            headers={"X-Api-Key": "sk_test", "Connection": "keep-alive", "X-Client": "ok"},
            params={"debug": "1"},
            json={"message": "hello"},
        )

    assert response.status_code == 202
    assert response.json() == {"ok": True}
    assert response.headers["x-upstream"] == "kept"
    assert "connection" not in response.headers
    request = route.calls.last.request
    assert request.url.params["debug"] == "1"
    assert request.headers["X-Client"] == "ok"
    assert request.headers["X-Organization-UUID"] == "org-1"
    assert request.headers["X-Project-UUID"] == "11111111-1111-1111-1111-111111111111"
    assert request.headers["X-API-Key-UUID"] == "api-key-1"
    assert json.loads(request.headers["X-Permissions"])[0] == "conversation.read"
    assert authenticated_gateway_api["gateway"].calls[0] == ("getDestination", "chat")
    assert authenticated_gateway_api["gateway"].calls[1][0] == "checkPermission"


@pytest.mark.asyncio
async def test_gateway_root_route_currently_requires_full_path(
    gateway_client,
    authenticated_gateway_api,
) -> None:
    response = await gateway_client.get("/chat", headers={"X-Api-Key": "sk_test"})

    assert response.status_code in {400, 422}
