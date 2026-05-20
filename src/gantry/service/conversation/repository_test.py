from .models import Message, ConversationType
from .repository import ConversationRepository

import unittest
from uuid import UUID
from types import SimpleNamespace
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock


class ConversationRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_conversation_metadata_by_uuid_maps_row(self):
        conversation = SimpleNamespace(
            id=1,
            uuid=UUID("123e4567-e89b-12d3-a456-426614174000"),
            project_id=10,
            extra_metadata={"topic": "demo"},
            created_at=datetime(2026, 1, 15),
            tree_structure={"m2": "m1"},
            active_leaf_message_id=UUID("123e4567-e89b-12d3-a456-426614174001"),
            conversation_type=ConversationType.SEQUENCE,
            relationships_map={"m1": "m2"},
        )
        result = MagicMock()
        result.scalar_one_or_none.return_value = conversation
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = ConversationRepository()

        metadata = await repo.getConversationMetadataByUUID(
            session,
            conversation_uuid=conversation.uuid,
            project_id=10,
        )

        assert metadata == {
            "conversation_id": 1,
            "conversation_uid": conversation.uuid,
            "project_id": 10,
            "extra_metadata": {"topic": "demo"},
            "created_at": datetime(2026, 1, 15),
            "tree_structure": {"m2": "m1"},
            "active_leaf_message_id": UUID(
                "123e4567-e89b-12d3-a456-426614174001"
            ),
            "conversation_type": ConversationType.SEQUENCE,
            "relationships_map": {"m1": "m2"},
        }

    async def test_get_message_by_uuid_returns_row(self):
        message = Message(
            conversation_id=1,
            payload={"type": "text", "content": "hello"},
            timestamp=datetime(2026, 1, 15),
            run_id="run-1",
            extra_metadata={"source": "test"},
        )
        result = MagicMock()
        result.scalar_one_or_none.return_value = message
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = ConversationRepository()

        found = await repo.getMessageByUuid(
            session,
            conversation_uuid=UUID("123e4567-e89b-12d3-a456-426614174000"),
            project_id=10,
            message_uid=message.uuid,
        )

        assert found is message

    async def test_get_messages_by_uuids_returns_rows(self):
        message = Message(
            conversation_id=1,
            payload={"type": "text", "content": "hello"},
            timestamp=datetime(2026, 1, 15),
            run_id=None,
            extra_metadata=None,
        )
        result = MagicMock()
        result.scalars.return_value.all.return_value = [message]
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = ConversationRepository()

        rows = await repo.getMessagesByUuids(
            session,
            conversation_uuid=UUID("123e4567-e89b-12d3-a456-426614174000"),
            project_id=10,
            message_uids=[message.uuid],
        )

        assert rows == [message]

    async def test_delete_conversation_by_uuid_returns_deleted_id(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = 7
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = ConversationRepository()

        deleted_id = await repo.deleteConversationByUUID(
            session,
            conversation_uuid=UUID("123e4567-e89b-12d3-a456-426614174000"),
            project_id=10,
        )

        assert deleted_id == 7
