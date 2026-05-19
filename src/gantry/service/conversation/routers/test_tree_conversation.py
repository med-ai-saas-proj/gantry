import json
import uuid
import asyncio
from typing import Any
from datetime import datetime, timezone
from collections import defaultdict

import httpx


BASE_URL = "http://localhost:8000/service/v1/conversations/tree"
API_KEY = "bypass_key"
TOTAL_BRANCHES = 10
TURNS_PER_BRANCH = 50

HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json",
}


class Variables:
    conversation_uid: str | None = None
    root_message_uid: str | None = None
    branch_leaf_map: dict[int, str] = {}
    branch_messages: dict[int, list[str]] = defaultdict(list)


variables = Variables()


MESSAGE_VARIANTS: list[dict[str, Any]] = [
    {
        "role": "user",
        "content": "tree user text message",
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "assistant branch response",
            }
        ],
    },
    {
        "role": "system",
        "content": "tree system instruction",
    },
    {
        "role": "tool",
        "toolCallId": "tool-branch-call",
        "toolName": "calculator_tool",
        "content": {
            "result": 999,
        },
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "tool-call",
                "toolCallId": "tool-branch-call-2",
                "toolName": "db_lookup",
                "args": {
                    "table": "users",
                    "id": 123,
                },
            }
        ],
    },
    {
        "role": "user",
        "content": [
            {
                "type": "audio",
                "url": "https://example.com/audio.mp3",
                "mimeType": "audio/mpeg",
            },
            {
                "type": "text",
                "text": "transcribe this audio",
            },
        ],
    },
]


def build_message(branch: int, turn: int) -> dict[str, Any]:
    payload = MESSAGE_VARIANTS[(branch + turn) % len(MESSAGE_VARIANTS)]

    return {
        "message_uid": str(uuid.uuid4()),
        "payload": payload,
        "run_id": f"branch-{branch}-turn-{turn}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "extra_metadata": {
            "branch": branch,
            "turn": turn,
            "path": f"branch-{branch}/{turn}",
            "complex_union": {
                "list": [1, "two", True],
                "object": {
                    "nested": "value",
                },
            },
        },
    }


async def create_conversation(client: httpx.AsyncClient):
    root_message = build_message(0, 0)

    response = await client.post(
        "/",
        headers=HEADERS,
        json={
            "extra_metadata": {
                "suite": "tree-branch-load-test",
            },
            "messages": [root_message],
        },
    )

    response.raise_for_status()

    data = response.json()

    variables.conversation_uid = data["conversation_uid"]
    variables.root_message_uid = root_message["message_uid"]

    print(f"[CREATE TREE] conversation_uid={variables.conversation_uid}")


async def build_branches(client: httpx.AsyncClient):
    for branch in range(TOTAL_BRANCHES):
        current_parent = variables.root_message_uid

        for turn in range(TURNS_PER_BRANCH):
            message = build_message(branch, turn)

            response = await client.post(
                f"/{variables.conversation_uid}/messages",
                headers=HEADERS,
                json={
                    "from_message_uid": current_parent,
                    "messages": [message],
                },
            )

            response.raise_for_status()

            current_parent = message["message_uid"]

            variables.branch_messages[branch].append(message["message_uid"])

            if turn % 10 == 0:
                print(f"[BRANCH={branch}] appended turn={turn}")

        variables.branch_leaf_map[branch] = current_parent


async def get_metadata(client: httpx.AsyncClient):
    response = await client.get(
        f"/{variables.conversation_uid}",
        headers=HEADERS,
    )

    response.raise_for_status()

    print("[TREE METADATA]")
    print(json.dumps(response.json(), indent=2))


async def get_branch_messages(client: httpx.AsyncClient):
    branch_leaf = variables.branch_leaf_map[0]

    response = await client.get(
        f"/{variables.conversation_uid}/messages",
        headers=HEADERS,
        params={
            "branch_message_uid": branch_leaf,
            "limit": 100,
            "order_by": "asc",
        },
    )

    response.raise_for_status()

    print(f"[GET BRANCH MESSAGES] count={len(response.json())}")


async def get_single_message(client: httpx.AsyncClient):
    message_uid = variables.branch_messages[2][20]

    response = await client.get(
        f"/{variables.conversation_uid}/messages/{message_uid}",
        headers=HEADERS,
    )

    response.raise_for_status()

    print(f"[GET SINGLE TREE MESSAGE] {message_uid}")


async def get_multiple_messages(client: httpx.AsyncClient):
    params: list[tuple[str, str]] = []

    for uid in variables.branch_messages[1][:15]:
        params.append(("message_uids", uid))

    response = await client.get(
        f"/{variables.conversation_uid}/messages",
        headers=HEADERS,
        params=params,
    )

    response.raise_for_status()

    print(f"[GET MULTIPLE TREE MESSAGES] count={len(response.json())}")


async def update_metadata(client: httpx.AsyncClient):
    response = await client.put(
        f"/{variables.conversation_uid}/metadata",
        headers=HEADERS,
        json={
            "extra_metadata": {
                "tree_updated": True,
                "branch_count": TOTAL_BRANCHES,
            }
        },
    )

    response.raise_for_status()

    print("[UPDATE TREE METADATA] success")


async def delete_message(client: httpx.AsyncClient):
    message_uid = variables.branch_messages[0][-1]

    response = await client.delete(
        f"/{variables.conversation_uid}/messages/{message_uid}",
        headers=HEADERS,
    )

    response.raise_for_status()

    print(f"[DELETE TREE MESSAGE] {message_uid}")


async def delete_conversation(client: httpx.AsyncClient):
    response = await client.delete(
        f"/{variables.conversation_uid}",
        headers=HEADERS,
    )

    response.raise_for_status()

    print(f"[DELETE TREE CONVERSATION] {variables.conversation_uid}")


async def main():
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=300,
    ) as client:
        await create_conversation(client)
        await build_branches(client)
        await get_metadata(client)
        await get_branch_messages(client)
        await get_single_message(client)
        await get_multiple_messages(client)
        await update_metadata(client)
        await delete_message(client)
        await delete_conversation(client)


if __name__ == "__main__":
    asyncio.run(main())
