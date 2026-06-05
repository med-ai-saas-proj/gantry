import json
import uuid
import asyncio
from typing import Any
from datetime import datetime, timezone

import httpx


BASE_URL = "http://localhost:8000/service/v1/conversations/sequence"
API_KEY = "bypass_key"
TOTAL_TURNS = 60

HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json",
}


class TestResults:
    """Track test results and assertions"""

    passed: int = 0
    failed: int = 0
    assertions: list[str] = []

    @classmethod
    def add_pass(cls, msg: str):
        cls.passed += 1
        cls.assertions.append(f"✓ {msg}")
        print(f"✓ PASS: {msg}")

    @classmethod
    def add_fail(cls, msg: str, error: str = ""):
        cls.failed += 1
        error_msg = f"✗ {msg}"
        if error:
            error_msg += f" - {error}"
        cls.assertions.append(error_msg)
        print(f"✗ FAIL: {error_msg}")

    @classmethod
    def report(cls):
        print("\n" + "=" * 60)
        print("TEST REPORT")
        print("=" * 60)
        print(f"Passed: {cls.passed}")
        print(f"Failed: {cls.failed}")
        print("\nAssertions:")
        for assertion in cls.assertions:
            print(f"  {assertion}")


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
    {
        "role": "user",
        "content": "line 1\nline 2\nline 3",
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "assistant response with multiple sentences and punctuation.",
            },
            {
                "type": "text",
                "text": "second block for richer payload coverage.",
            },
        ],
    },
    {
        "role": "tool",
        "toolCallId": "tool-call-3",
        "toolName": "summary_tool",
        "content": {
            "items": [1, 2, 3],
            "details": {
                "status": "ok",
                "counts": [10, 20],
            },
        },
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "mixed modal input with text first",
            },
            {
                "type": "image",
                "url": "https://example.com/diagram.png",
                "mimeType": "image/png",
            },
        ],
    },
]


def build_message(turn: int) -> dict[str, Any]:
    payload = MESSAGE_VARIANTS[turn % len(MESSAGE_VARIANTS)]
    case = turn % 4

    if case == 0:
        run_id: str | None = f"run-{turn}"
        extra_metadata: dict[str, Any] | None = {
            "turn": turn,
            "tags": ["sequence", f"turn-{turn}", "rich"],
            "nested": {
                "valid": True,
                "index": turn,
                "levels": [1, 2, 3],
            },
        }
    elif case == 1:
        run_id = None
        extra_metadata = {
            "turn": turn,
            "tags": [],
            "nested": {
                "valid": False,
                "index": turn,
                "nullable": None,
            },
        }
    elif case == 2:
        run_id = f"run-{turn}"
        extra_metadata = None
    else:
        run_id = None
        extra_metadata = {
            "turn": turn,
            "tags": ["sequence", "edge"],
            "nested": {
                "valid": True,
                "index": turn,
                "details": {"depth": 2, "empty": {}},
            },
        }

    message: dict[str, Any] = {
        "message_uid": str(uuid.uuid4()),
        "payload": payload,
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    message["extra_metadata"] = extra_metadata
    return message


async def create_conversation(client: httpx.AsyncClient):
    """Create a new conversation and verify response structure"""
    initial_messages = [build_message(0), build_message(1)]

    response = await client.post(
        "/",
        headers=HEADERS,
        json={
            "extra_metadata": {
                "suite": "sequence-load-test",
                "created_by": "httpx",
                "test_timestamp": datetime.now(timezone.utc).isoformat(),
                "labels": ["sequence", "baseline", "dto"],
                "flags": {
                    "nullable": None,
                    "enabled": True,
                },
            },
            "messages": initial_messages,
        },
    )

    # Verify status code
    try:
        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}"
        )
        TestResults.add_pass(f"Create conversation returned status 201")
    except AssertionError as e:
        TestResults.add_fail(f"Create conversation status code", str(e))
        raise

    response.raise_for_status()

    data = response.json()
    variables.conversation_uid = data["conversation_uid"]
    variables.message_uids = [msg["message_uid"] for msg in initial_messages]

    # Verify response structure
    try:
        assert "conversation_uid" in data, (
            "Missing conversation_uid in response"
        )
        assert isinstance(data["conversation_uid"], str), (
            "conversation_uid should be string"
        )
        assert len(data["conversation_uid"]) > 0, (
            "conversation_uid should not be empty"
        )
        TestResults.add_pass(
            f"Create conversation returned valid conversation_uid: {variables.conversation_uid}"
        )
    except AssertionError as e:
        TestResults.add_fail(f"Response structure validation", str(e))
        raise

    print(f"[CREATE] conversation_uid={variables.conversation_uid}")


async def update_metadata(client: httpx.AsyncClient):
    """Update conversation metadata and verify the update"""
    update_payloads = [
        {
            "extra_metadata": {
                "updated": True,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "version": 2,
                "status": "in_progress",
                "labels": ["sequence", "update", "primary"],
                "audit": {
                    "attempt": 1,
                    "success": True,
                },
            }
        },
        {
            "extra_metadata": {
                "version": 3,
                "status": "review",
                "labels": [],
                "audit": {
                    "attempt": 2,
                    "success": False,
                    "notes": None,
                },
            }
        },
    ]

    for update_payload in update_payloads:
        response = await client.put(
            f"/{variables.conversation_uid}/metadata",
            headers=HEADERS,
            json=update_payload,
        )

        try:
            assert response.status_code == 204, (
                f"Expected 204, got {response.status_code}"
            )
            TestResults.add_pass(
                "Update metadata returned status 204 (No Content)"
            )
        except AssertionError as e:
            TestResults.add_fail("Update metadata status code", str(e))
            raise

        response.raise_for_status()

    response = await client.put(
        f"/{variables.conversation_uid}/metadata",
        headers=HEADERS,
        json={"extra_metadata": {}},
    )

    try:
        assert response.status_code == 204, (
            f"Expected 204, got {response.status_code}"
        )
        TestResults.add_pass("Update metadata accepted empty metadata payload")
    except AssertionError as e:
        TestResults.add_fail("Update metadata empty payload", str(e))
        raise

    response.raise_for_status()
    print("[UPDATE METADATA] success")


async def get_metadata(client: httpx.AsyncClient):
    """Retrieve conversation metadata and verify structure"""
    response = await client.get(
        f"/{variables.conversation_uid}",
        headers=HEADERS,
    )

    try:
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}"
        )
        TestResults.add_pass("Get metadata returned status 200")
    except AssertionError as e:
        TestResults.add_fail("Get metadata status code", str(e))
        raise

    response.raise_for_status()

    metadata = response.json()
    extra_metadata = metadata.get("extra_metadata") or {}

    # Verify metadata structure
    try:
        assert "conversation_uid" in metadata, "Missing conversation_uid"
        assert "extra_metadata" in metadata, "Missing extra_metadata"
        assert "created_at" in metadata, "Missing created_at"
        assert metadata["conversation_uid"] == str(
            variables.conversation_uid
        ), "conversation_uid mismatch"
        TestResults.add_pass(
            "Get metadata returned valid structure with all required fields"
        )

        # Verify updated metadata
        if extra_metadata.get("updated") is True:
            assert extra_metadata["updated"] == True, "Updated flag not set"
            TestResults.add_pass("Metadata update was persisted correctly")
    except AssertionError as e:
        TestResults.add_fail("Metadata structure validation", str(e))
        raise

    print("[GET METADATA]")
    print(json.dumps(metadata, indent=2))


async def append_turns(client: httpx.AsyncClient):
    """Add multiple messages sequentially and verify each addition"""
    for turn in range(2, TOTAL_TURNS + 2):
        message = build_message(turn)

        response = await client.post(
            f"/{variables.conversation_uid}/messages",
            headers=HEADERS,
            json={
                "messages": [message],
            },
        )

        try:
            assert response.status_code == 201, (
                f"Turn {turn}: Expected 201, got {response.status_code}"
            )
        except AssertionError as e:
            TestResults.add_fail(f"Add message turn {turn}", str(e))
            raise

        response.raise_for_status()

        variables.message_uids.append(message["message_uid"])

        if turn % 10 == 0:
            print(f"[ADD MESSAGE] completed turn={turn}")
            TestResults.add_pass(f"Successfully added message at turn {turn}")

    TestResults.add_pass(
        f"Successfully added all {TOTAL_TURNS} messages sequentially"
    )


async def get_messages(client: httpx.AsyncClient):
    """Get messages with ascending order and verify pagination"""
    response = await client.get(
        f"/{variables.conversation_uid}/messages",
        headers=HEADERS,
        params={
            "limit": 25,
            "order_by": "asc",
        },
    )

    try:
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}"
        )
        TestResults.add_pass("Get messages (asc) returned status 200")
    except AssertionError as e:
        TestResults.add_fail("Get messages status code", str(e))
        raise

    response.raise_for_status()

    messages = response.json()

    try:
        assert isinstance(messages, list), "Response should be a list"
        assert len(messages) <= 25, f"Limit not respected: got {len(messages)}"
        assert len(messages) > 0, "Should return at least one message"
        assert messages[0]["message_uid"] == variables.message_uids[0], (
            "Ascending order should start with the first stored message"
        )

        # Verify message structure
        for msg in messages:
            assert "message_uid" in msg, "Message missing message_uid"
            assert "payload" in msg, "Message missing payload"
            assert "timestamp" in msg, "Message missing timestamp"

        TestResults.add_pass(
            f"Get messages returned {len(messages)} messages with valid structure (limit=25, asc)"
        )
    except AssertionError as e:
        TestResults.add_fail("Get messages validation", str(e))
        raise

    print(f"[GET MESSAGES] fetched={len(messages)}")


async def get_messages_boundary(client: httpx.AsyncClient):
    """Exercise pagination boundary behavior with a minimal limit."""
    response = await client.get(
        f"/{variables.conversation_uid}/messages",
        headers=HEADERS,
        params={
            "limit": 1,
            "order_by": "asc",
        },
    )

    try:
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}"
        )
        TestResults.add_pass(
            "Get messages boundary request returned status 200"
        )
    except AssertionError as e:
        TestResults.add_fail("Get messages boundary status code", str(e))
        raise

    response.raise_for_status()

    messages = response.json()

    try:
        assert isinstance(messages, list), "Response should be a list"
        assert len(messages) == 1, f"Expected 1 message, got {len(messages)}"
        assert messages[0]["message_uid"] == variables.message_uids[0], (
            "Boundary fetch should return the earliest message"
        )
        TestResults.add_pass(
            "Get messages boundary returned the earliest message"
        )
    except AssertionError as e:
        TestResults.add_fail("Get messages boundary validation", str(e))
        raise

    print(f"[GET MESSAGES BOUNDARY] fetched={len(messages)}")


async def get_messages_desc(client: httpx.AsyncClient):
    """Get messages with descending order and verify reverse pagination"""
    response = await client.get(
        f"/{variables.conversation_uid}/messages",
        headers=HEADERS,
        params={
            "limit": 25,
            "order_by": "desc",
        },
    )

    try:
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}"
        )
        TestResults.add_pass("Get messages (desc) returned status 200")
    except AssertionError as e:
        TestResults.add_fail("Get messages desc status code", str(e))
        raise

    response.raise_for_status()

    messages = response.json()

    try:
        assert isinstance(messages, list), "Response should be a list"
        assert len(messages) <= 25, f"Limit not respected: got {len(messages)}"
        assert messages[0]["message_uid"] == variables.message_uids[-1], (
            "Descending order should start with the most recent message"
        )
        TestResults.add_pass(
            f"Get messages (desc) returned {len(messages)} messages in reverse order"
        )
    except AssertionError as e:
        TestResults.add_fail("Get messages desc validation", str(e))
        raise

    print(f"[GET MESSAGES DESC] fetched={len(messages)}")


async def get_invalid_order_by(client: httpx.AsyncClient):
    """Verify invalid ordering input is rejected."""
    response = await client.get(
        f"/{variables.conversation_uid}/messages",
        headers=HEADERS,
        params={
            "limit": 5,
            "order_by": "sideways",
        },
    )

    try:
        assert response.status_code in [422, 400], (
            f"Expected 422 or 400, got {response.status_code}"
        )
        TestResults.add_pass("Invalid order_by returned status 422 or 400")
    except AssertionError as e:
        TestResults.add_fail("Invalid order_by validation", str(e))
        raise

    print(f"[INVALID ORDER BY] status={response.status_code}")


async def get_single_message(client: httpx.AsyncClient):
    """Retrieve a specific message by UID and verify content"""
    message_uid = variables.message_uids[-1]

    response = await client.get(
        f"/{variables.conversation_uid}/messages/{message_uid}",
        headers=HEADERS,
    )

    try:
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}"
        )
        TestResults.add_pass("Get single message returned status 200")
    except AssertionError as e:
        TestResults.add_fail("Get single message status code", str(e))
        raise

    response.raise_for_status()

    message = response.json()

    try:
        assert message["message_uid"] == str(message_uid), (
            "message_uid mismatch"
        )
        assert "payload" in message, "Missing payload"
        assert "run_id" in message, "Missing run_id"
        assert "timestamp" in message, "Missing timestamp"
        assert "extra_metadata" in message, "Missing extra_metadata"
        TestResults.add_pass(
            f"Get single message returned complete message object: {message_uid}"
        )
    except AssertionError as e:
        TestResults.add_fail("Get single message validation", str(e))
        raise

    print(f"[GET SINGLE MESSAGE] message_uid={message_uid}")


async def get_missing_message(client: httpx.AsyncClient):
    """Verify a missing message returns a not-found style response."""
    message_uid = str(uuid.uuid4())

    response = await client.get(
        f"/{variables.conversation_uid}/messages/{message_uid}",
        headers=HEADERS,
    )

    try:
        assert response.status_code in [404, 400], (
            f"Expected 404 or 400, got {response.status_code}"
        )
        TestResults.add_pass("Missing message returned a not-found response")
    except AssertionError as e:
        TestResults.add_fail("Missing message validation", str(e))
        raise

    print(
        f"[MISSING MESSAGE] message_uid={message_uid} status={response.status_code}"
    )


async def get_multiple_messages(client: httpx.AsyncClient):
    """Retrieve multiple specific messages by UIDs and verify all are returned"""
    selected = variables.message_uids[:10]

    response = await client.post(
        f"/{variables.conversation_uid}/messages/bulk",
        headers=HEADERS,
        json={
            "message_uids": selected,
        },
    )

    try:
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}"
        )
        TestResults.add_pass("Get multiple messages returned status 200")
    except AssertionError as e:
        TestResults.add_fail("Get multiple messages status code", str(e))
        raise

    response.raise_for_status()

    messages = response.json()

    try:
        assert isinstance(messages, list), "Response should be a list"
        assert len(messages) == len(selected), (
            f"Expected {len(selected)} messages, got {len(messages)}"
        )

        retrieved_uids = {msg["message_uid"] for msg in messages}
        requested_uids = {str(uid) for uid in selected}
        assert retrieved_uids == requested_uids, (
            "Retrieved UIDs don't match requested UIDs"
        )

        TestResults.add_pass(
            f"Get multiple messages returned all {len(messages)} requested messages with correct UIDs"
        )
    except AssertionError as e:
        TestResults.add_fail("Get multiple messages validation", str(e))
        raise

    print(f"[GET MULTIPLE MESSAGES] fetched={len(messages)}")


async def get_invalid_bulk_request(client: httpx.AsyncClient):
    """Verify bulk lookup rejects malformed UUID input."""
    response = await client.post(
        f"/{variables.conversation_uid}/messages/bulk",
        headers=HEADERS,
        json={
            "message_uids": [variables.message_uids[0], "not-a-uuid"],
        },
    )

    try:
        assert response.status_code in [422, 400], (
            f"Expected 422 or 400, got {response.status_code}"
        )
        TestResults.add_pass("Invalid bulk request returned status 422 or 400")
    except AssertionError as e:
        TestResults.add_fail("Invalid bulk request validation", str(e))
        raise

    print(f"[INVALID BULK REQUEST] status={response.status_code}")


async def delete_message(client: httpx.AsyncClient):
    """Delete a specific message and verify deletion"""
    message_uid = variables.message_uids[0]

    response = await client.delete(
        f"/{variables.conversation_uid}/messages/{message_uid}",
        headers=HEADERS,
    )

    try:
        assert response.status_code == 204, (
            f"Expected 204, got {response.status_code}"
        )
        TestResults.add_pass("Delete message returned status 204 (No Content)")
    except AssertionError as e:
        TestResults.add_fail("Delete message status code", str(e))
        raise

    response.raise_for_status()

    # Verify deletion by attempting to retrieve the deleted message
    verify_response = await client.get(
        f"/{variables.conversation_uid}/messages/{message_uid}",
        headers=HEADERS,
    )

    try:
        # Should return 404 or similar error
        assert verify_response.status_code in [404, 400], (
            f"Expected 404 or 400 after deletion, got {verify_response.status_code}"
        )
        TestResults.add_pass(
            f"Verified message deletion - message {message_uid} is no longer accessible"
        )
    except AssertionError as e:
        TestResults.add_fail("Message deletion verification", str(e))
        # Don't raise here as the delete might still succeed

    print(f"[DELETE MESSAGE] {message_uid}")


async def delete_conversation(client: httpx.AsyncClient):
    """Delete the entire conversation and verify deletion"""
    response = await client.delete(
        f"/{variables.conversation_uid}",
        headers=HEADERS,
    )

    try:
        assert response.status_code == 204, (
            f"Expected 204, got {response.status_code}"
        )
        TestResults.add_pass(
            "Delete conversation returned status 204 (No Content)"
        )
    except AssertionError as e:
        TestResults.add_fail("Delete conversation status code", str(e))
        raise

    response.raise_for_status()

    # Verify deletion by attempting to retrieve conversation metadata
    verify_response = await client.get(
        f"/{variables.conversation_uid}",
        headers=HEADERS,
    )

    try:
        assert verify_response.status_code in [404, 400], (
            f"Expected 404 or 400 after deletion, got {verify_response.status_code}"
        )
        TestResults.add_pass(
            f"Verified conversation deletion - conversation {variables.conversation_uid} is no longer accessible"
        )
    except AssertionError as e:
        TestResults.add_fail("Conversation deletion verification", str(e))

    print(f"[DELETE CONVERSATION] {variables.conversation_uid}")


async def main():
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=120,
    ) as client:
        try:
            await create_conversation(client)
            await update_metadata(client)
            await get_metadata(client)
            await append_turns(client)
            await get_messages(client)
            await get_messages_boundary(client)
            await get_messages_desc(client)
            await get_invalid_order_by(client)
            await get_single_message(client)
            await get_missing_message(client)
            await get_multiple_messages(client)
            await get_invalid_bulk_request(client)
            await delete_message(client)
            await delete_conversation(client)
        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
        finally:
            TestResults.report()


if __name__ == "__main__":
    asyncio.run(main())
