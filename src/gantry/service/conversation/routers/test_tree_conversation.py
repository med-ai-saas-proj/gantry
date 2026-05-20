import json
import uuid
import random
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
    branch_switch_source_uid: str | None = None
    message_parent_map: dict[str, str] = {}


variables = Variables()


def assert_tree_message_uids(
    messages: list[dict[str, Any]], expected_uids: list[str], context: str
) -> None:
    actual_uids = [msg["message_uid"] for msg in messages]
    assert actual_uids == expected_uids, (
        f"{context}: expected UIDs {expected_uids}, got {actual_uids}"
    )


def assert_tree_structure(metadata: dict[str, Any]) -> None:
    tree_structure = metadata.get("tree_structure")
    active_leaf_message_id = metadata.get("active_leaf_message_id")

    assert isinstance(tree_structure, dict), "tree_structure should be a dict"
    assert metadata.get("conversation_type") == "TREE", (
        f"Expected tree conversation type, got {metadata.get('conversation_type')}"
    )
    assert variables.root_message_uid in tree_structure, (
        "Root message uid should exist in tree_structure"
    )
    assert tree_structure[variables.root_message_uid] == str(
        uuid.UUID(int=0)
    ), "Root message should map to the tree sentinel root"
    latest_branch_index = max(variables.branch_leaf_map)
    latest_branch_leaf = variables.branch_leaf_map[latest_branch_index]
    assert active_leaf_message_id == latest_branch_leaf, (
        "Active leaf should match the latest modified branch leaf"
    )

    current_node = active_leaf_message_id
    seen_nodes: list[str] = []
    while current_node and current_node != str(uuid.UUID(int=0)):
        seen_nodes.append(current_node)
        current_node = tree_structure.get(current_node)

    assert variables.root_message_uid in seen_nodes, (
        "Active leaf ancestry should reach the root message"
    )

    if variables.branch_switch_source_uid is not None:
        assert (
            tree_structure[active_leaf_message_id]
            == variables.branch_switch_source_uid
        ), "Active leaf should be linked to the selected source message"
        assert variables.branch_switch_source_uid in seen_nodes, (
            "Selected source message should be in the active leaf ancestry"
        )


def build_expected_tree_path(leaf_uid: str | None) -> list[str]:
    if leaf_uid is None:
        return []

    path: list[str] = []
    current_uid = leaf_uid
    root_sentinel = str(uuid.UUID(int=0))

    while current_uid != root_sentinel:
        path.append(current_uid)
        current_uid = variables.message_parent_map.get(current_uid)
        if current_uid is None:
            break

    if variables.root_message_uid is not None and (
        not path or path[-1] != variables.root_message_uid
    ):
        path.append(variables.root_message_uid)

    path.reverse()
    return path


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
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "tree response with extra detail for branch coverage.",
            },
            {
                "type": "text",
                "text": "secondary block in the same assistant payload.",
            },
        ],
    },
    {
        "role": "tool",
        "toolCallId": "tool-branch-call-3",
        "toolName": "analysis_tool",
        "content": {
            "summary": "branch analytics",
            "scores": [0.25, 0.5, 0.75],
            "flags": {
                "stable": True,
                "reviewed": False,
            },
        },
    },
    {
        "role": "user",
        "content": "branch text with\nmultiple\nlines",
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "tool-call",
                "toolCallId": "tool-branch-call-4",
                "toolName": "search_tool",
                "args": {
                    "query": "branch edge case lookup",
                    "top_k": 3,
                },
            }
        ],
    },
]


def build_message(branch: int, turn: int) -> dict[str, Any]:
    payload = MESSAGE_VARIANTS[(branch + turn) % len(MESSAGE_VARIANTS)]
    case = (branch + turn) % 4

    if case == 0:
        run_id: str | None = f"branch-{branch}-turn-{turn}"
        extra_metadata: dict[str, Any] | None = {
            "branch": branch,
            "turn": turn,
            "path": f"branch-{branch}/{turn}",
            "complex_union": {
                "list": [1, "two", True],
                "object": {
                    "nested": "value",
                    "levels": [1, 2, 3],
                },
            },
        }
    elif case == 1:
        run_id = None
        extra_metadata = {
            "branch": branch,
            "turn": turn,
            "path": f"branch-{branch}/{turn}",
            "complex_union": {
                "list": [],
                "object": {
                    "nested": "value",
                    "nullable": None,
                },
            },
        }
    elif case == 2:
        run_id = f"branch-{branch}-turn-{turn}"
        extra_metadata = None
    else:
        run_id = None
        extra_metadata = {
            "branch": branch,
            "turn": turn,
            "path": f"branch-{branch}/{turn}",
            "complex_union": {
                "list": ["edge", 0, False],
                "object": {
                    "nested": "value",
                    "flags": {"seen": True},
                },
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
    """Create a new tree conversation with root message and verify structure"""
    root_message = build_message(0, 0)

    response = await client.post(
        "/",
        headers=HEADERS,
        json={
            "extra_metadata": {
                "suite": "tree-branch-load-test",
                "test_timestamp": datetime.now(timezone.utc).isoformat(),
                "labels": ["tree", "baseline", "dto"],
                "flags": {
                    "nullable": None,
                    "enabled": True,
                },
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
    root_message_uid = variables.root_message_uid
    assert root_message_uid is not None
    variables.message_parent_map[root_message_uid] = str(uuid.UUID(int=0))

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
    available_parent_uids = [variables.root_message_uid]
    current_parent = variables.root_message_uid
    for branch in range(TOTAL_BRANCHES):
        for turn in range(TURNS_PER_BRANCH):
            current_parent = random.choice(available_parent_uids)
            assert current_parent is not None
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

            variables.branch_messages[branch].append(message["message_uid"])
            variables.message_parent_map[message["message_uid"]] = (
                current_parent
            )
            available_parent_uids.append(message["message_uid"])

            if turn % 10 == 0:
                print(
                    f"[BRANCH={branch}] appended turn={turn} parent={current_parent}"
                )

        assert current_parent is not None
        variables.branch_leaf_map[branch] = current_parent
        TestResults.add_pass(
            f"Successfully built complete branch {branch} with {TURNS_PER_BRANCH} turns"
        )

    TestResults.add_pass(
        f"Successfully built all {TOTAL_BRANCHES} branches with {TURNS_PER_BRANCH} turns each"
    )


async def switch_branch_from_random_message(client: httpx.AsyncClient):
    """Create a new branch from a randomly selected existing message."""
    source_branch = random.choice(list(variables.branch_messages.keys()))
    source_message_uid = random.choice(variables.branch_messages[source_branch])
    source_turn = len(variables.branch_messages[source_branch])
    switch_message = build_message(source_branch, source_turn)

    response = await client.post(
        f"/{variables.conversation_uid}/messages",
        headers=HEADERS,
        json={
            "from_message_uid": source_message_uid,
            "messages": [switch_message],
        },
    )

    try:
        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}"
        )
        TestResults.add_pass(
            f"Branch switch from random message {source_message_uid} returned status 201"
        )
    except AssertionError as e:
        TestResults.add_fail("Branch switch status code", str(e))
        raise

    response.raise_for_status()

    variables.branch_switch_source_uid = source_message_uid
    switch_branch_index = max(variables.branch_leaf_map) + 1
    variables.branch_messages[switch_branch_index] = [
        switch_message["message_uid"]
    ]
    variables.branch_leaf_map[switch_branch_index] = switch_message[
        "message_uid"
    ]
    variables.message_parent_map[switch_message["message_uid"]] = (
        source_message_uid
    )

    TestResults.add_pass(
        f"Tracked switched branch leaf {switch_message['message_uid']} from source {source_message_uid}"
    )

    print(
        f"[SWITCH BRANCH] source={source_message_uid} new_leaf={switch_message['message_uid']}"
    )


async def add_branch_with_invalid_parent(client: httpx.AsyncClient):
    """Verify that branching from a non-existent parent is rejected."""
    message = build_message(0, 1)

    response = await client.post(
        f"/{variables.conversation_uid}/messages",
        headers=HEADERS,
        json={
            "from_message_uid": str(uuid.uuid4()),
            "messages": [message],
        },
    )

    try:
        assert response.status_code in [404, 400, 422], (
            f"Expected 404, 400, or 422, got {response.status_code}"
        )
        TestResults.add_pass("Invalid parent branch request was rejected")
    except AssertionError as e:
        TestResults.add_fail("Invalid parent branch validation", str(e))
        raise

    print(f"[INVALID PARENT BRANCH] status={response.status_code}")


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
    extra_metadata = metadata.get("extra_metadata") or {}

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

        assert_tree_structure(metadata)
        TestResults.add_pass(
            "Tree metadata structure and root linkage are valid"
        )
    except AssertionError as e:
        TestResults.add_fail("Tree metadata structure validation", str(e))
        raise

    print("[TREE METADATA]")
    print(json.dumps(metadata, indent=2))


async def get_branch_messages(client: httpx.AsyncClient):
    """Get messages from a specific branch using branch_message_uid parameter"""
    branch_leaf = variables.branch_leaf_map[0]
    expected_uids = build_expected_tree_path(branch_leaf)

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

        assert_tree_message_uids(
            messages,
            expected_uids[: len(messages)],
            "Branch message ordering",
        )

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


async def get_branch_messages_boundary(client: httpx.AsyncClient):
    """Exercise branch pagination with a minimal limit."""
    branch_leaf = variables.branch_leaf_map[0]
    expected_uids = build_expected_tree_path(branch_leaf)

    response = await client.get(
        f"/{variables.conversation_uid}/messages",
        headers=HEADERS,
        params={
            "branch_message_uid": branch_leaf,
            "limit": 1,
            "order_by": "asc",
        },
    )

    try:
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}"
        )
        TestResults.add_pass("Get branch boundary messages returned status 200")
    except AssertionError as e:
        TestResults.add_fail("Get branch boundary status code", str(e))
        raise

    response.raise_for_status()

    messages = response.json()

    try:
        assert isinstance(messages, list), "Response should be a list"
        assert len(messages) == 1, f"Expected 1 message, got {len(messages)}"
        assert messages[0]["message_uid"] == expected_uids[0], (
            "Boundary fetch should return the root message"
        )
        TestResults.add_pass("Get branch boundary returned a single message")
    except AssertionError as e:
        TestResults.add_fail("Get branch boundary validation", str(e))
        raise

    print(f"[GET BRANCH BOUNDARY] count={len(messages)}")


async def get_branch_messages_with_cursor(client: httpx.AsyncClient):
    """Verify cursor-based pagination on a specific branch."""
    branch_leaf = variables.branch_leaf_map[0]
    expected_uids = build_expected_tree_path(branch_leaf)

    first_page_response = await client.get(
        f"/{variables.conversation_uid}/messages",
        headers=HEADERS,
        params={
            "branch_message_uid": branch_leaf,
            "limit": 5,
            "order_by": "asc",
        },
    )

    try:
        assert first_page_response.status_code == 200, (
            f"Expected 200, got {first_page_response.status_code}"
        )
        TestResults.add_pass("Branch cursor first page returned status 200")
    except AssertionError as e:
        TestResults.add_fail("Branch cursor first page status", str(e))
        raise

    first_page_response.raise_for_status()
    first_page_messages = first_page_response.json()

    try:
        assert isinstance(first_page_messages, list), (
            "Response should be a list"
        )
        assert len(first_page_messages) == 5, (
            f"Expected 5 messages, got {len(first_page_messages)}"
        )
        assert_tree_message_uids(
            first_page_messages,
            expected_uids[:5],
            "Branch cursor first page ordering",
        )
        assert first_page_messages[0]["message_uid"] == expected_uids[0], (
            "First cursor page should start with the root message"
        )
    except AssertionError as e:
        TestResults.add_fail("Branch cursor first page validation", str(e))
        raise

    cursor = first_page_messages[-1]["message_uid"]

    second_page_response = await client.get(
        f"/{variables.conversation_uid}/messages",
        headers=HEADERS,
        params={
            "branch_message_uid": branch_leaf,
            "last_cursor": cursor,
            "limit": 3,
            "order_by": "asc",
        },
    )

    try:
        assert second_page_response.status_code == 200, (
            f"Expected 200, got {second_page_response.status_code}"
        )
        TestResults.add_pass("Branch cursor second page returned status 200")
    except AssertionError as e:
        TestResults.add_fail("Branch cursor second page status", str(e))
        raise

    second_page_response.raise_for_status()
    second_page_messages = second_page_response.json()

    try:
        assert isinstance(second_page_messages, list), (
            "Response should be a list"
        )
        assert len(second_page_messages) <= 3, (
            f"Expected at most 3 messages, got {len(second_page_messages)}"
        )

        first_page_uids = {msg["message_uid"] for msg in first_page_messages}
        second_page_uids = {msg["message_uid"] for msg in second_page_messages}
        assert first_page_uids.isdisjoint(second_page_uids), (
            "Cursor pagination returned overlapping branch messages"
        )

        for msg in second_page_messages:
            assert msg.get("extra_metadata", {}).get("branch") == 0, (
                "Cursor page included a message from the wrong branch"
            )

        if second_page_messages:
            assert_tree_message_uids(
                second_page_messages,
                expected_uids[5 : 5 + len(second_page_messages)],
                "Branch cursor second page ordering",
            )

        TestResults.add_pass(
            "Branch cursor pagination returned non-overlapping results"
        )
    except AssertionError as e:
        TestResults.add_fail("Branch cursor pagination validation", str(e))
        raise

    print(
        f"[GET BRANCH CURSOR] first={len(first_page_messages)} second={len(second_page_messages)}"
    )


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


async def get_missing_message(client: httpx.AsyncClient):
    """Verify a non-existent tree message returns a not-found response."""
    message_uid = str(uuid.uuid4())

    response = await client.get(
        f"/{variables.conversation_uid}/messages/{message_uid}",
        headers=HEADERS,
    )

    try:
        assert response.status_code in [404, 400], (
            f"Expected 404 or 400, got {response.status_code}"
        )
        TestResults.add_pass(
            "Missing tree message returned a not-found response"
        )
    except AssertionError as e:
        TestResults.add_fail("Missing tree message validation", str(e))
        raise

    print(
        f"[MISSING TREE MESSAGE] message_uid={message_uid} status={response.status_code}"
    )


async def get_multiple_messages(client: httpx.AsyncClient):
    """Retrieve multiple messages from different branches by UIDs"""
    response = await client.post(
        f"/{variables.conversation_uid}/messages/bulk",
        headers=HEADERS,
        json={
            "message_uids": variables.branch_messages[1][:15],
        },
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
        assert {msg["message_uid"] for msg in messages} == set(
            variables.branch_messages[1][:15]
        ), "Bulk tree message lookup returned unexpected message UUIDs"
        TestResults.add_pass(
            f"Get multiple tree messages returned all {len(messages)} requested messages"
        )
    except AssertionError as e:
        TestResults.add_fail("Get multiple messages validation", str(e))
        raise

    print(f"[GET MULTIPLE TREE MESSAGES] count={len(messages)}")


async def get_invalid_bulk_request(client: httpx.AsyncClient):
    """Verify bulk lookup rejects malformed UUID input."""
    response = await client.post(
        f"/{variables.conversation_uid}/messages/bulk",
        headers=HEADERS,
        json={
            "message_uids": [variables.branch_messages[1][0], "not-a-uuid"],
        },
    )

    try:
        assert response.status_code in [422, 400], (
            f"Expected 422 or 400, got {response.status_code}"
        )
        TestResults.add_pass(
            "Invalid tree bulk request returned status 422 or 400"
        )
    except AssertionError as e:
        TestResults.add_fail("Invalid tree bulk request validation", str(e))
        raise

    print(f"[INVALID TREE BULK REQUEST] status={response.status_code}")


async def get_invalid_order_by(client: httpx.AsyncClient):
    """Verify invalid ordering input is rejected for tree reads."""
    response = await client.get(
        f"/{variables.conversation_uid}/messages",
        headers=HEADERS,
        params={
            "branch_message_uid": variables.branch_leaf_map[0],
            "limit": 5,
            "order_by": "sideways",
        },
    )

    try:
        assert response.status_code in [422, 400], (
            f"Expected 422 or 400, got {response.status_code}"
        )
        TestResults.add_pass("Invalid tree order_by returned status 422 or 400")
    except AssertionError as e:
        TestResults.add_fail("Invalid tree order_by validation", str(e))
        raise

    print(f"[INVALID TREE ORDER BY] status={response.status_code}")


async def update_metadata(client: httpx.AsyncClient):
    """Update tree conversation metadata"""
    update_payloads = [
        {
            "extra_metadata": {
                "tree_updated": True,
                "branch_count": TOTAL_BRANCHES,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "labels": ["tree", "update", "primary"],
                "audit": {
                    "attempt": 1,
                    "success": True,
                },
            }
        },
        {
            "extra_metadata": {
                "tree_updated": True,
                "branch_count": TOTAL_BRANCHES,
                "updated_at": datetime.now(timezone.utc).isoformat(),
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
            TestResults.add_pass("Update tree metadata returned status 204")
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
        TestResults.add_pass(
            "Update tree metadata accepted empty metadata payload"
        )
    except AssertionError as e:
        TestResults.add_fail("Update tree metadata empty payload", str(e))
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
            await add_branch_with_invalid_parent(client)
            await build_branches(client)
            await switch_branch_from_random_message(client)
            await get_metadata(client)
            await get_branch_messages(client)
            await get_branch_messages_boundary(client)
            await get_branch_messages_with_cursor(client)
            await get_single_message(client)
            await get_missing_message(client)
            await get_multiple_messages(client)
            await get_invalid_bulk_request(client)
            await get_invalid_order_by(client)
            await update_metadata(client)
            await delete_message(client)
            await delete_conversation(client)
        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
        finally:
            TestResults.report()


if __name__ == "__main__":
    asyncio.run(main())
