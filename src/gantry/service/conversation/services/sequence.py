from pyrusult import Ok, Err, Result, ResultStatus
from gantry.db.session import AsyncSessionManager
from gantry.shared.utils.json_utils import json_serializer
from gantry.shared.utils.uuid_utils import uuid7

from .core import (
    ConversationService,
    ConversationNotFoundError,
    InvalidConversationTypeError,
)
from ..dtos import Message as RequestMessage
from ..models import (
    Message,
    Conversation,
    ConversationType,
)
from ..settings import ConversationSettings
from .serializer import Serializer
from ..repository import ConversationRepository
from ...file_storage.services import FileStorageService

import re
import json
import uuid
import asyncio
from time import timezone
from typing import Literal, Sequence, Awaitable, cast
from datetime import UTC
from dataclasses import asdict

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

        cache_key = ConversationService._message_list_cache_key(
            conversation_uid
        )
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
            cached_messages = [
                Message.parse_raw(json.loads(msg)) for msg in result
            ]
            return cached_messages[:limit]
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
        msgs: Sequence[RequestMessage],
    ) -> Result[None, ConversationNotFoundError | InvalidConversationTypeError]:
        if len(msgs) == 0:
            return Ok(None)
        return await self._storeConversationMessagesWithCache(
            is_new_conversation=False,
            conversation_uid=conversation_uid,
            project_id=project_id,
            serialized_msgs=[
                Message(
                    uuid=msg.message_uid,
                    conversation_id=-1,
                    payload=msg.payload
                    if isinstance(msg.payload, dict)
                    else msg.payload.model_dump(),
                    timestamp=msg.timestamp.astimezone(UTC).replace(
                        tzinfo=None
                    ),
                    extra_metadata=msg.extra_metadata,
                    run_id=msg.run_id,
                )
                for msg in msgs
            ]
            if msgs is not None
            else [],
        )

    # create a new conversation with given messages if conversation_id is None,
    # otherwise append messages to existing conversation
    # with cache update to keep cache and db consistent
    async def _storeConversationMessagesWithCache(
        self,
        is_new_conversation: bool,
        conversation_uid: uuid.UUID,
        project_id: int,
        serialized_msgs: Sequence[Message],
        extra_metadata: dict | None = None,
    ) -> Result[None, ConversationNotFoundError | InvalidConversationTypeError]:
        async with self.session_manager.get_session() as session:
            if is_new_conversation:
                conversation = Conversation(
                    uuid=conversation_uid,
                    project_id=project_id,
                    extra_metadata=extra_metadata,
                    conversation_type=ConversationType.SEQUENCE,
                    tree_structure=None,
                    active_leaf_message_id=None,
                    relationships_map=None,
                )
                session.add(conversation)
                await session.flush()
                conversation_id = conversation.id
            else:
                conversation_metadata = (
                    await self.conversation_repo.getConversationMetadataByUUID(
                        session, conversation_uid, project_id
                    )
                )
                if conversation_metadata is None:
                    return Err(ConversationNotFoundError())
                if (
                    conversation_metadata["conversation_type"]
                    != ConversationType.SEQUENCE
                ):
                    return Err(InvalidConversationTypeError())
                conversation_id = conversation_metadata["conversation_id"]

            if len(serialized_msgs) > 0:
                for msg in serialized_msgs:
                    msg.conversation_id = conversation_id
                session.add_all(serialized_msgs)
                await session.flush()
            await session.commit()

        if len(serialized_msgs) > 0:
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
        return Ok(None)

    # avoid appending to cache when cache is not loaded to prevent cache have only new messages but miss old messages
    async def _tryAppendConversationMessagesCache(
        self, conversation_uid: uuid.UUID, msgs: Sequence[Message]
    ):
        cache_key = ConversationService._message_list_cache_key(
            conversation_uid
        )
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
        cache_key = ConversationService._message_list_cache_key(
            conversation_uid
        )
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
        messages: Sequence[RequestMessage] | None,
    ) -> Result[
        uuid.UUID, ConversationNotFoundError | InvalidConversationTypeError
    ]:
        conversation_uid = uuid7()
        res = await self._storeConversationMessagesWithCache(
            is_new_conversation=True,
            conversation_uid=conversation_uid,
            project_id=project_id,
            extra_metadata=extra_metadata,
            serialized_msgs=[
                Message(
                    uuid=msg.message_uid,
                    conversation_id=-1,
                    payload=msg.payload
                    if isinstance(msg.payload, dict)
                    else msg.payload.model_dump(),
                    timestamp=msg.timestamp.astimezone(UTC).replace(
                        tzinfo=None
                    ),
                    extra_metadata=msg.extra_metadata,
                    run_id=msg.run_id,
                )
                for msg in messages
            ]
            if messages is not None
            else [],
        )

        if res.status == ResultStatus.Err:
            return res.into()
        return Ok(conversation_uid)


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
        is_new_conversation: bool,
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
        (
            await self._storeConversationMessagesWithCache(
                is_new_conversation=is_new_conversation,
                conversation_uid=conversation_uid,
                project_id=project_id,
                serialized_msgs=serialized_msgs,
            )
        ).unwrap()
