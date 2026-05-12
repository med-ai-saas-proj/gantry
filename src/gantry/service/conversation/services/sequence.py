from gantry.db.session import AsyncSessionManager
from gantry.shared.utils.json_utils import json_serializer
from gantry.shared.utils.uuid_utils import uuid7

from .core import ConversationService, ConversationNotFoundError
from ..dtos import RequestMessage, ResponseMessage
from ..types import (
    MessagePart,
)
from ..models import (
    Message,
    Conversation,
    ConversationType,
)
from ..settings import ConversationSettings
from .serializer import Serializer
from ..repository import ConversationRepository
from ...file_storage.services import FileStorageService

import json
import uuid
import asyncio
from typing import Literal, Sequence, Awaitable, cast
from dataclasses import asdict

from pyrusult import Ok, Err, Result, ResultStatus
from redis.asyncio import Redis


class SequenceConversationService(ConversationService):
    """Implements a conversation service where messages are stored in a single sequence, and the entire sequence is retrieved for each request."""

    async def getConversationMessages(
        self,
        conversation_uid: uuid.UUID,
        project_id: int,
        limit: int = 20,
        last_cursor: uuid.UUID | None = None,
        order_by: Literal["asc", "desc"] = "asc",
    ) -> Result[Sequence[Message], ConversationNotFoundError]:
        async with self.session_manager.get_session() as session:
            metadata = (
                await self.conversation_repo.getConversationMetadataByUUID(
                    session, conversation_uid, project_id
                )
            )
            if metadata is None:
                return Err(ConversationNotFoundError())
        messages = await self._getConversationMessagesWithCache(
            metadata["conversation_id"],
            conversation_uid,
            limit=limit,
            last_cursor=last_cursor,
            order_by=order_by,
        )
        return Ok(messages)

    async def _getConversationMessagesFromDB(
        self,
        conversation_id: int,
        limit: int = 20,
        last_cursor: uuid.UUID | None = None,
        order_by: Literal["asc", "desc"] = "asc",
    ) -> Sequence[Message]:
        async with self.session_manager.get_session() as session:
            msgs = await self.conversation_repo.getMessagesByConversationId(
                session,
                conversation_id,
                limit=limit,
                last_cursor=last_cursor,
                order_by=order_by,
            )
            session.expunge_all()
        return msgs

    async def _getConversationMessagesWithCache(
        self,
        conversation_id: int,
        conversation_uid: uuid.UUID,
        limit: int = 20,
        last_cursor: uuid.UUID | None = None,
        order_by: Literal["asc", "desc"] = "asc",
    ) -> Sequence[Message]:
        can_cache = (
            last_cursor is None
            and order_by == "desc"
            and limit <= self.setting.cache_limit
        )
        if not can_cache:
            return await self._getConversationMessagesFromDB(
                conversation_id,
                limit=limit,
                last_cursor=last_cursor,
                order_by=order_by,
            )

        cache_key = ConversationService._message_cache_key(conversation_uid)
        # atomic check if cache exists and is ready, if so get from cache, otherwise get from db and update cache
        lua_script = """
           if redis.call('EXISTS', KEYS[1]) == 1 then
                redis.call('EXPIRE', KEYS[1], ARGV[1])
                return redis.call('ZREVRANGE', KEYS[1], 0, -1)
           else
               return nil
           end
           """
        result = await cast(
            Awaitable[list[str] | None],
            self.redis_client.eval(
                lua_script, 1, cache_key, self.setting.cache_ttl
            ),
        )
        if result is not None:
            return [Message.parse_raw(json.loads(msg)) for msg in result]
        msgs = await self._getConversationMessagesFromDB(
            conversation_id,
            limit=self.setting.cache_limit,
            last_cursor=last_cursor,
            order_by=order_by,
        )
        await self._addConversationMessagesCache(conversation_uid, msgs)
        return msgs

    async def storeConversationMessages(
        self,
        conversation_uid: uuid.UUID,
        project_id: int,
        msgs: Sequence[RequestMessage | ResponseMessage],
    ) -> Result[None, ConversationNotFoundError]:
        res = await self.getConversationMetadata(conversation_uid, project_id)
        if res.status == ResultStatus.Err:
            return res.into()
        metadata = res.unwrap()
        await self._storeConversationMessagesWithCache(
            metadata["conversation_id"],
            conversation_uid,
            project_id,
            [
                Message(
                    conversation_id=-1,
                    kind=msg.kind,
                    parts=cast(list[MessagePart], msg.parts),
                    timestamp=msg.timestamp,
                    model_name=msg.model_name
                    if hasattr(msg, "model_name")
                    else None,
                    run_id=msg.run_id if hasattr(msg, "run_id") else None,
                )
                for msg in msgs
            ]
            if msgs is not None
            else [],
            conversation_type=ConversationType.SEQUENCE,
        )
        return Ok(None)

    # create a new conversation with given messages if conversation_id is None,
    # otherwise append messages to existing conversation
    # with cache update to keep cache and db consistent
    async def _storeConversationMessagesWithCache(
        self,
        conversation_id: int | None,
        conversation_uid: uuid.UUID,
        project_id: int,
        serialized_msgs: Sequence[Message],
        conversation_type: ConversationType,
        extra_metadata: dict | None = None,
    ):
        is_new_conversation = conversation_id is None
        if conversation_id is None:
            async with self.session_manager.get_session() as session:
                conversation = Conversation(
                    uuid=conversation_uid,
                    project_id=project_id,
                    extra_metadata=extra_metadata,
                    conversation_type=conversation_type,
                    tree_structure=None,
                    activePath=None,
                )
                session.add(conversation)
                await session.flush()
                conversation_id = conversation.id
                await session.commit()

        for msg in serialized_msgs:
            msg.conversation_id = conversation_id

        if len(serialized_msgs) > 0:
            async with self.session_manager.get_session() as session:
                session.add_all(serialized_msgs)
                await session.flush()
                await session.commit()
            if is_new_conversation:
                # create new cache for the conversation, no need to check if cache exists as it's a new conversation
                await self._addConversationMessagesCache(
                    conversation_uid, serialized_msgs
                )
            else:
                # append to cache if cache exists, if cache does not exist then do nothing and let next read update the cache (avoid appending to cache when cache is not loaded to prevent cache have only new messages but miss old messages)
                await self._tryAppendConversationMessagesCache(
                    conversation_uid, serialized_msgs
                )

    # avoid appending to cache when cache is not loaded to prevent cache have only new messages but miss old messages
    async def _tryAppendConversationMessagesCache(
        self, conversation_uid: uuid.UUID, msgs: Sequence[Message]
    ):
        cache_key = ConversationService._message_cache_key(conversation_uid)
        # atomic check if cache exists and is ready,
        # if so append to cache, otherwise do nothing and let next read update the cache
        # (avoid appending to cache when cache is not loaded
        # to prevent cache have only new messages but miss old messages)
        append_script = """
        -- ARGV: message_id1, msg1, message_id2, msg2, ..., ttl, cache_limit
        -- check if cache exists, if not exist then return 0
        local ttl = tonumber(ARGV[#ARGV - 1])
        local limit = tonumber(ARGV[#ARGV])
        if redis.call('EXISTS', KEYS[1]) then
            for i = 1, #ARGV-2, 2 do
                redis.call('ZADD', KEYS[1], ARGV[i], ARGV[i+1])
            end
            redis.call('EXPIRE', KEYS[1], ttl)
            -- trim to cache limit
            redis.call('ZREMRANGEBYRANK', KEYS[1], 0, -limit-1)
            return 1
        else
            return 0
        end
        """
        mappings: list[str | int] = []
        for msg in msgs:
            mappings.append(
                msg.id
            )  # use database id (ascending) as score to maintain correct order in cache
            mappings.append(json.dumps(asdict(msg), default=json_serializer))
        mappings.append(self.setting.cache_ttl)
        mappings.append(self.setting.cache_limit)
        res = await cast(
            Awaitable[int],
            self.redis_client.eval(
                append_script,
                1,
                cache_key,
                *mappings,
            ),
        )

    async def _addConversationMessagesCache(
        self, conversation_uid: uuid.UUID, msgs: Sequence[Message]
    ):
        if len(msgs) == 0:
            return
        cache_key = ConversationService._message_cache_key(conversation_uid)
        mappings = {
            json.dumps(asdict(msg), default=json_serializer): msg.id
            for msg in msgs
        }

        async with self.redis_client.pipeline(
            transaction=True,
        ) as pipe:
            await pipe.zadd(cache_key, mappings)
            await pipe.zremrangebyrank(
                cache_key, 0, -self.setting.cache_limit - 1
            )
            await pipe.expire(cache_key, self.setting.cache_ttl)
            await pipe.execute()

    async def createConversation(
        self,
        project_id: int,
        extra_metadata: dict | None,
        messages: Sequence[RequestMessage | ResponseMessage] | None,
    ):
        conversation_uid = uuid7()
        await self._storeConversationMessagesWithCache(
            conversation_id=None,
            conversation_uid=conversation_uid,
            project_id=project_id,
            extra_metadata=extra_metadata,
            serialized_msgs=[
                Message(
                    conversation_id=-1,
                    kind=msg.kind,
                    parts=cast(list[MessagePart], msg.parts),
                    timestamp=msg.timestamp,
                    model_name=msg.model_name if msg.model_name else None,
                    run_id=msg.run_id if msg.run_id else None,
                )
                for msg in messages
            ]
            if messages is not None
            else [],
            conversation_type=ConversationType.SEQUENCE,
        )
        return conversation_uid


class SequenceConversationWithSerializerService[T](SequenceConversationService):
    def __init__(
        self,
        session_manager: AsyncSessionManager,
        conversation_repo: ConversationRepository,
        file_service: FileStorageService,
        redis_client: Redis,
        setting: ConversationSettings,
        serializer: Serializer[T],
    ) -> None:
        super().__init__(
            session_manager,
            conversation_repo,
            file_service,
            redis_client,
            setting,
        )
        self.serializer = serializer

    async def getAndDeserializeConversationMessages(
        self,
        conversation_id: int,
        conversation_uid: uuid.UUID,
        project_id: int,
        limit: int = 20,
    ) -> Sequence[T]:
        serialized_msgs = await self._getConversationMessagesWithCache(
            conversation_id,
            conversation_uid,
            limit=limit,
            order_by="desc",
        )
        tasks = [
            self.serializer.deserializeConversationMessages(
                msg, project_id=project_id
            )
            for msg in serialized_msgs
        ]
        msgs = await asyncio.gather(*tasks)
        return list(reversed(msgs))

    async def serializeAndStoreConversationMessages(
        self,
        conversation_id: int | None,
        conversation_uid: uuid.UUID,
        project_id: int,
        msgs: Sequence[T],
    ) -> None:
        tasks = [
            self.serializer.serializeConversationMessages(
                conversation_id=-1, msg=msg
            )
            for msg in msgs
        ]
        serialized_msgs = await asyncio.gather(*tasks)
        await self._storeConversationMessagesWithCache(
            conversation_id,
            conversation_uid,
            project_id,
            serialized_msgs,
            conversation_type=ConversationType.SEQUENCE,
        )
