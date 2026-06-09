from __future__ import annotations

import pytest

from tests.api.fakes import CONVERSATION_UUID

pytestmark = pytest.mark.api

AUTH = {"X-Api-Key": "sk_test"}
MESSAGE_UUID = "66666666-6666-6666-6666-666666666666"


@pytest.mark.asyncio
async def test_conversation_metadata_and_message_lifecycle_routes(service_client, authenticated_service_api) -> None:
    created = await service_client.post(
        "/v1/conversations/sequence/",
        headers=AUTH,
        json={"extra_metadata": {"topic": "demo"}},
    )
    metadata = await service_client.get(f"/v1/conversations/sequence/{CONVERSATION_UUID}", headers=AUTH)
    updated = await service_client.put(
        f"/v1/conversations/sequence/{CONVERSATION_UUID}/metadata",
        headers=AUTH,
        json={"extra_metadata": {"topic": "updated"}},
    )
    messages = await service_client.get(
        f"/v1/conversations/sequence/{CONVERSATION_UUID}/messages",
        headers=AUTH,
        params={"limit": 5, "order_by": "desc"},
    )
    add_message = await service_client.post(
        f"/v1/conversations/sequence/{CONVERSATION_UUID}/messages",
        headers=AUTH,
        json={"messages": []},
    )
    message = await service_client.get(
        f"/v1/conversations/sequence/{CONVERSATION_UUID}/messages/{MESSAGE_UUID}",
        headers=AUTH,
    )
    delete_message = await service_client.delete(
        f"/v1/conversations/sequence/{CONVERSATION_UUID}/messages/{MESSAGE_UUID}",
        headers=AUTH,
    )
    deleted = await service_client.delete(f"/v1/conversations/sequence/{CONVERSATION_UUID}", headers=AUTH)

    assert created.status_code == 201
    assert created.json()["conversation_uid"] == CONVERSATION_UUID
    assert metadata.json()["extra_metadata"] == {"topic": "demo"}
    assert updated.status_code == 204
    assert messages.status_code == 200
    assert len(messages.json()) == 5
    assert add_message.status_code == 201
    assert message.status_code == 200
    assert message.json()["message_uid"] == MESSAGE_UUID
    assert delete_message.status_code == 204
    assert deleted.status_code == 204
    assert authenticated_service_api["sequence_conversation"].calls[0][0] == "createConversation"


@pytest.mark.asyncio
async def test_conversation_pagination_validation(service_client, authenticated_service_api) -> None:
    response = await service_client.get(
        f"/v1/conversations/sequence/{CONVERSATION_UUID}/messages",
        headers=AUTH,
        params={"limit": 0},
    )

    assert response.status_code in {400, 422}
