from __future__ import annotations

import httpx
import pytest
import respx

pytestmark = pytest.mark.api


@pytest.mark.asyncio
async def test_external_identity_metadata_contract_is_mocked_with_respx() -> None:
    url = "https://identity.test/realms/gantry/.well-known/openid-configuration"
    with respx.mock(assert_all_called=True) as router:
        router.get(url).mock(
            return_value=httpx.Response(
                200,
                json={
                    "issuer": "https://identity.test/realms/gantry",
                    "token_endpoint": "https://identity.test/token",
                },
            )
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(url)

    assert response.status_code == 200
    assert response.json()["issuer"].endswith("/realms/gantry")
