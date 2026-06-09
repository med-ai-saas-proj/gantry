from gantry.service.conversation.models import Message, ConversationType
from gantry.service.conversation.settings import ConversationSettings
from gantry.service.conversation.repository import ConversationRepository
from gantry.service.conversation.services.core import (
    ConversationService,
    MessageNotFoundError,
    ConversationNotFoundError,
)

import json
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


class ConversationServiceTest(unittest.IsolatedAsyncioTestCase):
    def _build_service(
        self,
        repo: ConversationRepository,
        redis_client: MagicMock,
        session: MagicMock,
    ):
        setting = ConversationSettings(cache_ttl=60, cache_limit=50)
        return ConversationService(
            session_manager=cast(Any, _SessionManager(session)),
            conversation_repo=repo,
            file_service=MagicMock(),
            redis_client=redis_client,
            setting=setting,
        )

    async def test_get_conversation_metadata_returns_cached_json(self):
        session = MagicMock()
        redis_client = MagicMock()
        redis_client.get = AsyncMock(
            return_value=json.dumps({"conversation_id": 1})
        )
        repo = MagicMock(spec=ConversationRepository)
        service = self._build_service(repo, redis_client, session)

        res = await service.getConversationMetadata(
            UUID("123e4567-e89b-12d3-a456-426614174000"),
            project_id=10,
        )

        assert res.status == ResultStatus.Ok
        assert res.unwrap() == {"conversation_id": 1}
        repo.getConversationMetadataByUUID.assert_not_called()

    async def test_get_conversation_metadata_loads_and_caches_when_missing(
        self,
    ):
        session = MagicMock()
        session.expunge_all = MagicMock()
        redis_client = MagicMock()
        redis_client.get = AsyncMock(return_value=None)
        redis_client.set = AsyncMock()
        repo = MagicMock(spec=ConversationRepository)
        repo.getConversationMetadataByUUID = AsyncMock(
            return_value={
                "conversation_id": 1,
                "conversation_uid": UUID(
                    "123e4567-e89b-12d3-a456-426614174000"
                ),
                "project_id": 10,
                "extra_metadata": {"topic": "demo"},
                "created_at": datetime(2026, 1, 15),
                "tree_structure": None,
                "active_leaf_message_id": None,
                "relationships_map": None,
                "conversation_type": ConversationType.SEQUENCE,
            }
        )
        service = self._build_service(repo, redis_client, session)

        res = await service.getConversationMetadata(
            UUID("123e4567-e89b-12d3-a456-426614174000"),
            project_id=10,
        )

        assert res.status == ResultStatus.Ok
        assert res.unwrap()["conversation_id"] == 1
        redis_client.set.assert_awaited_once()

    async def test_get_conversation_message_by_uuid_loads_and_populates_cache(
        self,
    ):
        session = MagicMock()
        session.expunge_all = MagicMock()
        redis_client = MagicMock()
        redis_client.hget = AsyncMock(return_value=None)
        repo = MagicMock(spec=ConversationRepository)
        message = Message(
            uuid=UUID("123e4567-e89b-12d3-a456-426614174001"),
            conversation_id=1,
            payload={"type": "text", "content": "hello"},
            timestamp=datetime(2026, 1, 15),
            run_id="run-1",
            extra_metadata=None,
        )
        repo.getMessageByUuid = AsyncMock(return_value=message)
        service = self._build_service(repo, redis_client, session)
        service.addConversationMessagesCache = AsyncMock()

        res = await service.getConversationMessageByUuid(
            UUID("123e4567-e89b-12d3-a456-426614174000"),
            project_id=10,
            message_uid=message.uuid,
        )

        assert res.status == ResultStatus.Ok
        assert res.unwrap() is message
        service.addConversationMessagesCache.assert_awaited_once()

    async def test_delete_conversation_message_returns_err_when_missing(self):
        session = MagicMock()
        session.commit = AsyncMock()
        redis_client = MagicMock()
        repo = MagicMock(spec=ConversationRepository)
        repo.deleteMessageByUuid = AsyncMock(return_value=None)
        service = self._build_service(repo, redis_client, session)

        res = await service.deleteConversationMessage(
            UUID("123e4567-e89b-12d3-a456-426614174000"),
            project_id=10,
            message_uid=UUID("123e4567-e89b-12d3-a456-426614174001"),
        )

        assert res.status == ResultStatus.Err
        assert isinstance(res.err(), MessageNotFoundError)

    async def test_update_conversation_metadata_commits(self):
        session = MagicMock()
        session.commit = AsyncMock()
        redis_client = MagicMock()
        repo = MagicMock(spec=ConversationRepository)
        repo.updateConversationMetadataByUUID = AsyncMock(
            return_value={"conversation_id": 1}
        )
        service = self._build_service(repo, redis_client, session)

        res = await service.updateConversationMetadata(
            UUID("123e4567-e89b-12d3-a456-426614174000"),
            project_id=10,
            extra_metadata={"topic": "demo"},
        )

        assert res.status == ResultStatus.Ok
        session.commit.assert_awaited_once()
