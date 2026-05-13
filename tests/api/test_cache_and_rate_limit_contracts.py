from __future__ import annotations

import json

import httpx
import pytest
import respx
from pyrusult import Ok

from gantry.api_gateway.factories import getApiGatewayService
from gantry.management.api_key.factories import getApiKeyService
from tests.api.fakes import FakeGatewayService
from tests.factories import ApiKeyInfoFactory

pytestmark = pytest.mark.api


class RedisBackedApiKeyService:
    """API-key service double that exercises cache and rate-limit Redis calls."""

    def __init__(self, redis) -> None:
        self.redis = redis
        self.calls: list[tuple[str, str]] = []

    async def parseApiKey(self, api_key: str):
        self.calls.append(("parseApiKey", api_key))
        cache_key = f"api-key-info:{api_key}"
        cached = await self.redis.get(cache_key)
        if cached is not None:
            return Ok(json.loads(cached))

        payload = ApiKeyInfoFactory(api_key_uuid="api-key-redis")
        await self.redis.set(cache_key, json.dumps(payload), ex=60)
        return Ok(payload)

    async def rateLimit(self, api_key_info: dict):
        self.calls.append(("rateLimit", api_key_info["api_key_uuid"]))
        key = f"api-key-rpm:{api_key_info['project_uuid']}"
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, 60)
        return Ok(True)


@pytest.mark.asyncio
async def test_gateway_api_key_dependency_uses_fakeredis_cache_and_rate_limit(
    gateway_client,
    gateway_override_dependencies,
    fake_redis,
) -> None:
    api_key_service = RedisBackedApiKeyService(fake_redis)
    gateway_service = FakeGatewayService()
    gateway_override_dependencies[getApiKeyService] = lambda: api_key_service
    gateway_override_dependencies[getApiGatewayService] = lambda: gateway_service

    upstream_url = "https://upstream.example/base/v1/messages"
    with respx.mock(assert_all_called=True) as router:
        router.get(upstream_url).mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        first = await gateway_client.get(
            "/chat/v1/messages",
            headers={"X-Api-Key": "sk_test"},
        )

    with respx.mock(assert_all_called=True) as router:
        router.get(upstream_url).mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        second = await gateway_client.get(
            "/chat/v1/messages",
            headers={"X-Api-Key": "sk_test"},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert await fake_redis.get("api-key-info:sk_test") is not None
    assert int(await fake_redis.get("api-key-rpm:11111111-1111-1111-1111-111111111111")) == 2
    assert api_key_service.calls == [
        ("parseApiKey", "sk_test"),
        ("rateLimit", "api-key-redis"),
        ("parseApiKey", "sk_test"),
        ("rateLimit", "api-key-redis"),
    ]
