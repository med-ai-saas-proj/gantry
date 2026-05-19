from gantry.service.conversation.models import Message, ConversationType
from gantry.service.conversation.settings import ConversationSettings
from gantry.service.conversation.repository import ConversationRepository
from gantry.service.conversation.services.tree import (
    ROOT_NODE_ID,
    TreeConversationService,
)

import unittest
from uuid import UUID
from types import SimpleNamespace
from typing import Any, cast
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from pyrusult import ResultStatus


class _AsyncContextManager:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _SessionManager:
    def __init__(self, session):
        self.session = session

    def get_session(self):
        return _AsyncContextManager(self.session)


class TreeConversationServiceTest(unittest.IsolatedAsyncioTestCase):
    def _build_service(
        self,
        repo: ConversationRepository,
        redis_client: MagicMock,
        session: MagicMock,
    ):
        setting = ConversationSettings(cache_ttl=60, cache_limit=50)
        return TreeConversationService(
            session_manager=cast(Any, _SessionManager(session)),
            conversation_repo=repo,
            file_service=MagicMock(),
            redis_client=redis_client,
            setting=setting,
        )

    async def test_rebuild_tree_structure_builds_tree_branch(self):
        session = MagicMock()
        repo = MagicMock(spec=ConversationRepository)
        service = self._build_service(repo, MagicMock(), session)
        messages = [
            Message(
                conversation_id=-1,
                payload={"type": "text", "content": "one"},
                timestamp=datetime(2026, 1, 15),
                run_id=None,
                extra_metadata=None,
            ),
            Message(
                conversation_id=-1,
                payload={"type": "text", "content": "two"},
                timestamp=datetime(2026, 1, 15),
                run_id=None,
                extra_metadata=None,
            ),
        ]

        structure, active_leaf_id = service.rebuildTreeStructure({}, messages)

        assert structure[str(messages[0].uuid)] == ROOT_NODE_ID
        assert structure[str(messages[1].uuid)] == str(messages[0].uuid)
        assert active_leaf_id == messages[1].uuid

    async def test_rebuild_relationships_map_builds_tree_relationships(self):
        session = MagicMock()
        repo = MagicMock(spec=ConversationRepository)
        service = self._build_service(repo, MagicMock(), session)
        messages = [
            Message(
                conversation_id=-1,
                payload={"type": "text", "content": "one"},
                timestamp=datetime(2026, 1, 15),
                run_id=None,
                extra_metadata=None,
            ),
            Message(
                conversation_id=-1,
                payload={"type": "text", "content": "two"},
                timestamp=datetime(2026, 1, 15),
                run_id=None,
                extra_metadata=None,
            ),
        ]

        rel_map = service.rebuildRelationshipsMap({}, messages)

        assert rel_map[ROOT_NODE_ID] == str(messages[0].uuid)
        assert rel_map[str(messages[0].uuid)] == str(messages[1].uuid)

    async def test_get_conversation_messages_returns_empty_when_branch_missing(
        self,
    ):
        session = MagicMock()
        repo = MagicMock(spec=ConversationRepository)
        repo.getConversationMetadataByUUID = AsyncMock(
            return_value={
                "conversation_id": 1,
                "conversation_uid": UUID(
                    "123e4567-e89b-12d3-a456-426614174000"
                ),
                "project_id": 10,
                "extra_metadata": None,
                "created_at": datetime(2026, 1, 15),
                "tree_structure": {},
                "active_leaf_message_id": None,
                "relationships_map": None,
                "conversation_type": ConversationType.TREE,
            }
        )
        service = self._build_service(repo, MagicMock(), session)

        res = await service.getConversationMessages(
            conversation_uid=UUID("123e4567-e89b-12d3-a456-426614174000"),
            project_id=10,
            branch_node_id=UUID("123e4567-e89b-12d3-a456-426614174001"),
        )

        assert res.status == ResultStatus.Ok
        assert res.unwrap() == []
