import json
import uuid
import asyncio
from typing import Any
from datetime import datetime, timezone

import httpx


BASE_URL = "http://localhost:8000/service/v1/conversations/tree"
API_KEY = "bypass_key"
TOTAL_TURNS = 60

HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json",
}


class Variables:
    conversation_uid: str | None = None
    message_uids: list[str] = []


variables = Variables()


MESSAGE_VARIANTS: list[dict[str, Any]] = [
    {
        "role": "user",
        "content": "plain text message",
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "assistant rich text response",
            }
        ],
    },
    {
        "role": "system",
        "content": "system instruction message",
    },
    {
        "role": "tool",
        "toolCallId": "tool-call-1",
        "toolName": "weather_tool",
        "content": {
            "temperature": 30,
            "unit": "C",
        },
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "tool-call",
                "toolCallId": "tool-call-2",
                "toolName": "search_tool",
                "args": {
                    "query": "latest AI news",
                },
            }
        ],
    },
    {
        "role": "user",
        "content": [
            {
                "type": "image",
                "url": "https://example.com/image.png",
                "mimeType": "image/png",
            },
            {
                "type": "text",
                "text": "describe this image",
            },
        ],
    },
]


def build_message(turn: int) -> dict[str, Any]:
    payload = MESSAGE_VARIANTS[turn % len(MESSAGE_VARIANTS)]

    return {
        "message_uid": str(uuid.uuid4()),
        "payload": payload,
        "run_id": f"run-{turn}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "extra_metadata": {
            "turn": turn,
            "tags": ["sequence", f"turn-{turn}"],
            "nested": {
                "valid": True,
                "index": turn,
            },
        },
    }


async def create_conversation(client: httpx.AsyncClient):
    initial_messages = [build_message(0), build_message(1)]

    response = await client.post(
        "/",
        headers=HEADERS,
        json={
            "extra_metadata": {
                "suite": "sequence-load-test",
                "created_by": "httpx",
            },
            "messages": initial_messages,
        },
    )

    response.raise_for_status()

    data = response.json()
    variables.conversation_uid = data["conversation_uid"]

    print(f"[CREATE] conversation_uid={variables.conversation_uid}")


async def update_metadata(client: httpx.AsyncClient):
    response = await client.put(
        f"/{variables.conversation_uid}/metadata",
        headers=HEADERS,
        json={
            "extra_metadata": {
                "updated": True,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )

    response.raise_for_status()
    print("[UPDATE METADATA] success")


async def get_metadata(client: httpx.AsyncClient):
    response = await client.get(
        f"/{variables.conversation_uid}",
        headers=HEADERS,
    )

    response.raise_for_status()

    print("[GET METADATA]")
    print(json.dumps(response.json(), indent=2))


async def append_turns(client: httpx.AsyncClient):
    for turn in range(2, TOTAL_TURNS + 2):
        message = build_message(turn)

        response = await client.post(
            f"/{variables.conversation_uid}/messages",
            headers=HEADERS,
            json={
                "messages": [message],
            },
        )

        response.raise_for_status()

        variables.message_uids.append(message["message_uid"])

        if turn % 10 == 0:
            print(f"[ADD MESSAGE] completed turn={turn}")


async def get_messages(client: httpx.AsyncClient):
    response = await client.get(
        f"/{variables.conversation_uid}/messages",
        headers=HEADERS,
        params={
            "limit": 25,
            "order_by": "asc",
        },
    )

    response.raise_for_status()

    messages = response.json()
    print(f"[GET MESSAGES] fetched={len(messages)}")


async def get_messages_desc(client: httpx.AsyncClient):
    response = await client.get(
        f"/{variables.conversation_uid}/messages",
        headers=HEADERS,
        params={
            "limit": 25,
            "order_by": "desc",
        },
    )

    response.raise_for_status()

    messages = response.json()
    print(f"[GET MESSAGES DESC] fetched={len(messages)}")


async def get_single_message(client: httpx.AsyncClient):
    message_uid = variables.message_uids[-1]

    response = await client.get(
        f"/{variables.conversation_uid}/messages/{message_uid}",
        headers=HEADERS,
    )

    response.raise_for_status()

    print(f"[GET SINGLE MESSAGE] message_uid={message_uid}")


async def get_multiple_messages(client: httpx.AsyncClient):
    selected = variables.message_uids[:10]

    params: list[tuple[str, str]] = []

    for uid in selected:
        params.append(("message_uids", uid))

    response = await client.get(
        f"/{variables.conversation_uid}/messages",
        headers=HEADERS,
        params=params,
    )

    response.raise_for_status()

    print(f"[GET MULTIPLE MESSAGES] fetched={len(response.json())}")


async def delete_message(client: httpx.AsyncClient):
    message_uid = variables.message_uids[0]

    response = await client.delete(
        f"/{variables.conversation_uid}/messages/{message_uid}",
        headers=HEADERS,
    )

    response.raise_for_status()

    print(f"[DELETE MESSAGE] message_uid={message_uid}")


async def delete_conversation(client: httpx.AsyncClient):
    response = await client.delete(
        f"/{variables.conversation_uid}",
        headers=HEADERS,
    )

    response.raise_for_status()

    print(f"[DELETE CONVERSATION] {variables.conversation_uid}")


async def main():
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=120,
    ) as client:
        await create_conversation(client)
        await update_metadata(client)
        await get_metadata(client)
        await append_turns(client)
        await get_messages(client)
        await get_messages_desc(client)
        await get_single_message(client)
        await get_multiple_messages(client)
        await delete_message(client)
        await delete_conversation(client)


if __name__ == "__main__":
    asyncio.run(main())
