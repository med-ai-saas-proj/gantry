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
        print("TEST REPORT - TREE CONVERSATION")
        print("=" * 60)
        print(f"Passed: {cls.passed}")
        print(f"Failed: {cls.failed}")
        print("\nAssertions:")
        for assertion in cls.assertions:
            print(f"  {assertion}")


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
    """Create a new tree conversation with root message and verify structure"""
    root_message = build_message(0, 0)

    response = await client.post(
        "/",
        headers=HEADERS,
        json={
            "extra_metadata": {
                "suite": "tree-branch-load-test",
                "test_timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "messages": [root_message],
        },
    )

    try:
        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}"
        )
        TestResults.add_pass("Create tree conversation returned status 201")
    except AssertionError as e:
        TestResults.add_fail("Create conversation status code", str(e))
        raise

    response.raise_for_status()

    data = response.json()

    variables.conversation_uid = data["conversation_uid"]
    variables.root_message_uid = root_message["message_uid"]

    try:
        assert "conversation_uid" in data, "Missing conversation_uid"
        assert isinstance(data["conversation_uid"], str), (
            "conversation_uid should be string"
        )
        TestResults.add_pass(
            f"Create tree conversation returned valid structure: {variables.conversation_uid}"
        )
    except AssertionError as e:
        TestResults.add_fail("Response structure validation", str(e))
        raise

    print(f"[CREATE TREE] conversation_uid={variables.conversation_uid}")


async def build_branches(client: httpx.AsyncClient):
    """Build multiple branches from root and verify tree structure integrity"""
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

            try:
                assert response.status_code == 201, (
                    f"Branch {branch}, Turn {turn}: Expected 201, got {response.status_code}"
                )
            except AssertionError as e:
                TestResults.add_fail(
                    f"Add branch message branch={branch} turn={turn}", str(e)
                )
                raise

            response.raise_for_status()

            current_parent = message["message_uid"]

            variables.branch_messages[branch].append(message["message_uid"])

            if turn % 10 == 0:
                print(f"[BRANCH={branch}] appended turn={turn}")

        variables.branch_leaf_map[branch] = current_parent
        TestResults.add_pass(
            f"Successfully built complete branch {branch} with {TURNS_PER_BRANCH} turns"
        )

    TestResults.add_pass(
        f"Successfully built all {TOTAL_BRANCHES} branches with {TURNS_PER_BRANCH} turns each"
    )


async def get_metadata(client: httpx.AsyncClient):
    """Get tree conversation metadata and verify tree structure fields"""
    response = await client.get(
        f"/{variables.conversation_uid}",
        headers=HEADERS,
    )

    try:
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}"
        )
        TestResults.add_pass("Get tree metadata returned status 200")
    except AssertionError as e:
        TestResults.add_fail("Get tree metadata status code", str(e))
        raise

    response.raise_for_status()

    metadata = response.json()

    # Verify tree-specific metadata structure
    try:
        assert "conversation_uid" in metadata, "Missing conversation_uid"
        assert "project_id" in metadata, "Missing project_id"
        assert "created_at" in metadata, "Missing created_at"
        assert "extra_metadata" in metadata, "Missing extra_metadata"
        TestResults.add_pass("Get tree metadata returned valid base structure")

        # Check for tree-specific fields
        tree_fields = [
            "tree_structure",
            "active_leaf_message_id",
            "conversation_type",
            "relationships_map",
        ]
        for field in tree_fields:
            if field in metadata:
                TestResults.add_pass(f"Tree metadata contains {field}")
    except AssertionError as e:
        TestResults.add_fail("Tree metadata structure validation", str(e))
        raise

    print("[TREE METADATA]")
    print(json.dumps(metadata, indent=2))


async def get_branch_messages(client: httpx.AsyncClient):
    """Get messages from a specific branch using branch_message_uid parameter"""
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

    try:
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}"
        )
        TestResults.add_pass("Get branch messages returned status 200")
    except AssertionError as e:
        TestResults.add_fail("Get branch messages status code", str(e))
        raise

    response.raise_for_status()

    messages = response.json()

    try:
        assert isinstance(messages, list), "Response should be a list"
        assert len(messages) > 0, "Branch should have at least one message"
        assert len(messages) <= 100, f"Limit not respected: got {len(messages)}"

        # Verify branch consistency
        for msg in messages:
            assert "message_uid" in msg, "Message missing message_uid"
            assert "extra_metadata" in msg, "Message missing extra_metadata"

        TestResults.add_pass(
            f"Get branch messages returned {len(messages)} messages for branch leaf {branch_leaf}"
        )
    except AssertionError as e:
        TestResults.add_fail("Get branch messages validation", str(e))
        raise

    print(f"[GET BRANCH MESSAGES] count={len(messages)}")


async def get_single_message(client: httpx.AsyncClient):
    """Get a specific message from the tree structure"""
    message_uid = variables.branch_messages[2][20]

    response = await client.get(
        f"/{variables.conversation_uid}/messages/{message_uid}",
        headers=HEADERS,
    )

    try:
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}"
        )
        TestResults.add_pass("Get single tree message returned status 200")
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
        assert "extra_metadata" in message, "Missing extra_metadata"
        assert "branch" in message["extra_metadata"], (
            "Missing branch in metadata"
        )
        TestResults.add_pass(
            f"Get single tree message returned complete message with branch info"
        )
    except AssertionError as e:
        TestResults.add_fail("Get single message validation", str(e))
        raise

    print(f"[GET SINGLE TREE MESSAGE] {message_uid}")


async def get_multiple_messages(client: httpx.AsyncClient):
    """Retrieve multiple messages from different branches by UIDs"""
    params: list[tuple[str, str]] = []

    for uid in variables.branch_messages[1][:15]:
        params.append(("message_uids", uid))

    response = await client.get(
        f"/{variables.conversation_uid}/messages/bulk",
        headers=HEADERS,
        params=params,
    )

    try:
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}. Response: {response.text}"
        )
        TestResults.add_pass("Get multiple tree messages returned status 200")
    except AssertionError as e:
        TestResults.add_fail("Get multiple messages status code", str(e))
        raise

    response.raise_for_status()

    messages = response.json()

    try:
        assert isinstance(messages, list), "Response should be a list"
        assert len(messages) == 15, f"Expected 15 messages, got {len(messages)}"
        TestResults.add_pass(
            f"Get multiple tree messages returned all {len(messages)} requested messages"
        )
    except AssertionError as e:
        TestResults.add_fail("Get multiple messages validation", str(e))
        raise

    print(f"[GET MULTIPLE TREE MESSAGES] count={len(messages)}")


async def update_metadata(client: httpx.AsyncClient):
    """Update tree conversation metadata"""
    response = await client.put(
        f"/{variables.conversation_uid}/metadata",
        headers=HEADERS,
        json={
            "extra_metadata": {
                "tree_updated": True,
                "branch_count": TOTAL_BRANCHES,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )

    try:
        assert response.status_code == 204, (
            f"Expected 204, got {response.status_code}"
        )
        TestResults.add_pass("Update tree metadata returned status 204")
    except AssertionError as e:
        TestResults.add_fail("Update metadata status code", str(e))
        raise

    response.raise_for_status()

    print("[UPDATE TREE METADATA] success")


async def delete_message(client: httpx.AsyncClient):
    """Delete a message from tree (leaf node) and verify deletion"""
    message_uid = variables.branch_messages[0][-1]

    response = await client.delete(
        f"/{variables.conversation_uid}/messages/{message_uid}",
        headers=HEADERS,
    )

    try:
        assert response.status_code == 204, (
            f"Expected 204, got {response.status_code}"
        )
        TestResults.add_pass("Delete tree message returned status 204")
    except AssertionError as e:
        TestResults.add_fail("Delete tree message status code", str(e))
        raise

    response.raise_for_status()

    # Verify deletion
    verify_response = await client.get(
        f"/{variables.conversation_uid}/messages/{message_uid}",
        headers=HEADERS,
    )

    try:
        assert verify_response.status_code in [404, 400], (
            f"Expected 404 or 400 after deletion, got {verify_response.status_code}"
        )
        TestResults.add_pass(f"Verified tree message deletion")
    except AssertionError as e:
        TestResults.add_fail("Message deletion verification", str(e))

    print(f"[DELETE TREE MESSAGE] {message_uid}")


async def delete_conversation(client: httpx.AsyncClient):
    """Delete the entire tree conversation"""
    response = await client.delete(
        f"/{variables.conversation_uid}",
        headers=HEADERS,
    )

    try:
        assert response.status_code == 204, (
            f"Expected 204, got {response.status_code}"
        )
        TestResults.add_pass("Delete tree conversation returned status 204")
    except AssertionError as e:
        TestResults.add_fail("Delete conversation status code", str(e))
        raise

    response.raise_for_status()

    # Verify deletion
    verify_response = await client.get(
        f"/{variables.conversation_uid}",
        headers=HEADERS,
    )

    try:
        assert verify_response.status_code in [404, 400], (
            f"Expected 404 or 400 after deletion, got {verify_response.status_code}"
        )
        TestResults.add_pass(f"Verified tree conversation deletion")
    except AssertionError as e:
        TestResults.add_fail("Conversation deletion verification", str(e))

    print(f"[DELETE TREE CONVERSATION] {variables.conversation_uid}")


async def main():
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=300,
    ) as client:
        try:
            await create_conversation(client)
            await build_branches(client)
            await get_metadata(client)
            await get_branch_messages(client)
            await get_single_message(client)
            await get_multiple_messages(client)
            await update_metadata(client)
            await delete_message(client)
            await delete_conversation(client)
        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
        finally:
            TestResults.report()


if __name__ == "__main__":
    asyncio.run(main())
