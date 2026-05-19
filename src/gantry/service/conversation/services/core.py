from gantry.db.session import AsyncSessionManager
from gantry.shared.utils.json_utils import json_serializer
from gantry.shared.custom_types.error_exception import RecoverableError

from ..types import (
    ConversationMetadata,
)
from ..models import (
    Message,
)
from ..settings import ConversationSettings
from ..repository import ConversationRepository
from ...file_storage.services import FileStorageService

import json
import uuid
from typing import Sequence, Awaitable, cast
from dataclasses import asdict

from pyrusult import Ok, Err, Result
from redis.asyncio import Redis


class InvalidConversationTypeError(RecoverableError):
    """Raised when the conversation type is invalid."""

    status = 400
    code = "invalid_conversation_type"
    title = "Invalid conversation type"
    detail = "The specified conversation type is invalid or not supported"


class ConversationNotFoundError(RecoverableError):
    """Raised when a conversation is not found."""

    status = 404
    code = "conversation_not_found"
    title = "Conversation not found"
    detail = "The specified conversation does not exist or is not accessible with the provided API key"


class MessageNotFoundError(RecoverableError):
    """Raised when a message is not found."""

    status = 404
    code = "message_not_found"
    title = "Message not found"
    detail = "The specified message does not exist in the conversation"


class ConversationService:
    def __init__(
        self,
        session_manager: AsyncSessionManager,
        conversation_repo: ConversationRepository,
        file_service: FileStorageService,
        redis_client: Redis,
        setting: ConversationSettings,
    ) -> None:
        """Initialize ConversationService."""
        self.redis_client = redis_client
        self.session_manager = session_manager
        self.conversation_repo = conversation_repo
        self.file_service = file_service
        self.setting = setting

    async def getConversationMetadata(
        self, conversation_uid: uuid.UUID, project_id: int
    ) -> Result[ConversationMetadata, ConversationNotFoundError]:
        """Get conversation metadata by its UID and project ID."""
        cache_key = ConversationService._conversation_cache_key(
            conversation_uid
        )
        cached_metadata = await cast(
            Awaitable[str | None], self.redis_client.get(cache_key)
        )
        if cached_metadata:
            return Ok(json.loads(cached_metadata))

        async with self.session_manager.get_session() as session:
            metadata = (
                await self.conversation_repo.getConversationMetadataByUUID(
                    session, conversation_uid, project_id
                )
            )
            if metadata is None:
                return Err(ConversationNotFoundError())

        await self.redis_client.set(
            cache_key,
            json.dumps(metadata, default=json_serializer),
            ex=self.setting.cache_ttl,
        )
        return Ok(metadata)

    async def getConversationMessageByUuid(
        self,
        conversation_uid: uuid.UUID,
        project_id: int,
        message_uid: uuid.UUID,
    ) -> Result[Message, MessageNotFoundError]:
        cache_key = ConversationService._message_set_cache_key(conversation_uid)
        cached_msg = await cast(
            Awaitable[str | None],
            self.redis_client.hget(cache_key, str(message_uid)),
        )
        if cached_msg:
            return Ok(Message.parse_raw(json.loads(cached_msg)))

        async with self.session_manager.get_session() as session:
            msg = await self.conversation_repo.getMessageByUuid(
                session, conversation_uid, project_id, message_uid
            )
            if msg is None:
                return Err(MessageNotFoundError())
            session.expunge_all()

        await self.addConversationMessagesCache(conversation_uid, [msg])
        return Ok(msg)

    async def getConversationMessagesByUuids(
        self,
        conversation_uid: uuid.UUID,
        project_id: int,
        message_uids: Sequence[uuid.UUID],
    ) -> Sequence[Message]:
        if len(message_uids) == 0:
            return []

        cache_key = ConversationService._message_set_cache_key(conversation_uid)
        raw_cached_msgs = await cast(
            Awaitable[list[str | None]],
            self.redis_client.hmget(
                cache_key, [str(uid) for uid in message_uids]
            ),
        )

        cached_msgs = [
            Message.parse_raw(json.loads(msg)) for msg in raw_cached_msgs if msg
        ]
        if len(cached_msgs) == len(message_uids):
            return cached_msgs

        cached_msg_uids = {msg.uuid for msg in cached_msgs}
        missing_uids = [
            uid for uid in message_uids if uid not in cached_msg_uids
        ]

        async with self.session_manager.get_session() as session:
            msgs = await self.conversation_repo.getMessagesByUuids(
                session, conversation_uid, project_id, missing_uids
            )
            session.expunge_all()

        await self.addConversationMessagesCache(conversation_uid, msgs)
        return [*cached_msgs, *msgs]

    async def addConversationMessagesCache(
        self, conversation_uid: uuid.UUID, msgs: Sequence[Message]
    ):
        if len(msgs) == 0:
            return
        cache_key = ConversationService._message_set_cache_key(conversation_uid)
        mappings = {
            str(msg.uuid): json.dumps(asdict(msg), default=json_serializer)
            for msg in msgs
        }

        async with self.redis_client.pipeline(
            transaction=True,
        ) as pipe:
            await cast(Awaitable[int], pipe.hset(cache_key, mapping=mappings))
            await pipe.expire(cache_key, self.setting.cache_ttl)
            await pipe.execute()

    async def deleteConversationMessage(
        self,
        conversation_uid: uuid.UUID,
        project_id: int,
        message_uid: uuid.UUID,
    ):
        async with self.session_manager.get_session() as session:
            deleted = await self.conversation_repo.deleteMessageByUuid(
                session, conversation_uid, project_id, message_uid
            )
            if deleted is None:
                return Err(MessageNotFoundError())
            await session.commit()

        await self.redis_client.delete(
            ConversationService._message_set_cache_key(conversation_uid)
        )
        await self.redis_client.delete(
            ConversationService._message_list_cache_key(conversation_uid)
        )
        return Ok(None)

    async def deleteConversation(
        self,
        conversation_uid: uuid.UUID,
        project_id: int,
    ):
        async with self.session_manager.get_session() as session:
            deleted = await self.conversation_repo.deleteConversationByUUID(
                session, conversation_uid, project_id
            )
            if deleted is None:
                return Err(ConversationNotFoundError())
            await session.commit()

        await self.redis_client.delete(
            ConversationService._conversation_cache_key(conversation_uid)
        )
        await self.redis_client.delete(
            ConversationService._message_list_cache_key(conversation_uid)
        )
        await self.redis_client.delete(
            ConversationService._message_set_cache_key(conversation_uid)
        )
        return Ok(None)

    @staticmethod
    def _conversation_cache_key(conversation_uid: uuid.UUID) -> str:
        return f"conv_cache:{{{conversation_uid}}}"

    @staticmethod
    def _message_list_cache_key(conversation_uid: uuid.UUID) -> str:
        return f"conv_mess_list_cache:{{{conversation_uid}}}"

    @staticmethod
    def _message_set_cache_key(conversation_uid: uuid.UUID) -> str:
        return f"conv_mess_set_cache:{{{conversation_uid}}}"

    async def updateConversationMetadata(
        self,
        conversation_uid: uuid.UUID,
        project_id: int,
        extra_metadata: dict | None,
    ):
        async with self.session_manager.get_session() as session:
            updated = (
                await self.conversation_repo.updateConversationMetadataByUUID(
                    session, conversation_uid, project_id, extra_metadata
                )
            )
            if updated is None:
                return Err(ConversationNotFoundError())
            await session.commit()
        return Ok(None)
