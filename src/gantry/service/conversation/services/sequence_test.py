from gantry.service.conversation.dtos import Message as RequestMessage
from gantry.service.conversation.models import Message
from gantry.service.conversation.settings import ConversationSettings
from gantry.service.conversation.repository import ConversationRepository
from gantry.service.conversation.services.sequence import (
    SequenceConversationService,
)

import unittest
from uuid import UUID
from types import SimpleNamespace
from typing import Any, cast
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from pyrusult import Ok, ResultStatus


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


class SequenceConversationServiceTest(unittest.IsolatedAsyncioTestCase):
    def _build_service(
        self,
        repo: ConversationRepository,
        redis_client: MagicMock,
        session: MagicMock,
    ):
        setting = ConversationSettings(cache_ttl=60, cache_limit=50)
        return SequenceConversationService(
            session_manager=cast(Any, _SessionManager(session)),
            conversation_repo=repo,
            file_service=MagicMock(),
            redis_client=redis_client,
            setting=setting,
        )

    async def test_store_conversation_messages_empty_returns_ok(self):
        session = MagicMock()
        repo = MagicMock(spec=ConversationRepository)
        service = self._build_service(repo, MagicMock(), session)

        res = await service.storeConversationMessages(
            conversation_uid=UUID("123e4567-e89b-12d3-a456-426614174000"),
            project_id=10,
            msgs=[],
        )

        assert res.status == ResultStatus.Ok

    async def test_get_conversation_messages_returns_err_when_missing(self):
        session = MagicMock()
        repo = MagicMock(spec=ConversationRepository)
        repo.getConversationMetadataByUUID = AsyncMock(return_value=None)
        service = self._build_service(repo, MagicMock(), session)

        res = await service.getConversationMessages(
            conversation_uid=UUID("123e4567-e89b-12d3-a456-426614174000"),
            project_id=10,
        )

        assert res.status == ResultStatus.Err

    async def test_create_conversation_delegates_to_internal_store(self):
        session = MagicMock()
        repo = MagicMock(spec=ConversationRepository)
        service = self._build_service(repo, MagicMock(), session)
        service._storeConversationMessagesWithCache = AsyncMock(
            return_value=Ok(None)
        )
        request_msg = RequestMessage(
            message_uid=UUID("123e4567-e89b-12d3-a456-426614174001"),
            payload={"type": "text", "content": "hello"},
            run_id="run-1",
            timestamp=datetime(2026, 1, 15),
            extra_metadata=None,
        )

        with patch(
            "gantry.service.conversation.services.sequence.uuid7",
            return_value=UUID("123e4567-e89b-12d3-a456-426614174000"),
        ):
            res = await service.createConversation(
                project_id=10,
                extra_metadata={"topic": "demo"},
                messages=[request_msg],
            )

        assert res.status == ResultStatus.Ok
        service._storeConversationMessagesWithCache.assert_awaited_once()
