from gantry.db.session import AsyncSessionManager
from gantry.shared.utils.json_utils import json_serializer
from gantry.shared.utils.uuid_utils import uuid7
from gantry.shared.custom_types.error_exception import InternalServiceError

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

import json
import uuid
import asyncio
from typing import Literal, Sequence, Awaitable, cast
from dataclasses import asdict

from pyrusult import Ok, Err, Result, ResultStatus
from redis.asyncio import Redis


class TreeConversationService(ConversationService):
    """Implements a conversation service where messages are stored in a single sequence, and the entire sequence is retrieved for each request."""

    async def getConversationMessages(
        self,
        conversation_uid: uuid.UUID,
        project_id: int,
        offset: int = 0,
        limit: int = 20,
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
            offset=offset,
            limit=limit,
            order_by=order_by,
        )
        return Ok(messages)

    async def _getConversationMessagesWithCache(
        self,
        conversation_id: int,
        conversation_uid: uuid.UUID,
        offset: int = 0,
        limit: int = 20,
        order_by: Literal["asc", "desc"] = "asc",
    ) -> Sequence[Message]:
        return []  # get active branch messages

    async def storeConversationMessages(
        self,
        conversation_uid: uuid.UUID,
        project_id: int,
        msgs: Sequence[RequestMessage],
    ) -> Result[
        None,
        ConversationNotFoundError
        | InvalidConversationTypeError
        | InternalServiceError,
    ]:
        if len(msgs) == 0:
            return Ok(None)
        return await self._storeConversationMessagesWithCache(
            is_new_conversation=False,
            conversation_uid=conversation_uid,
            project_id=project_id,
            serialized_msgs=[
                Message(
                    conversation_id=-1,
                    payload=msg.payload,
                    timestamp=msg.timestamp,
                    extra_metadata=msg.extra_metadata,
                    run_id=msg.run_id,
                )
                for msg in msgs
            ]
            if msgs is not None
            else [],
            conversation_type=ConversationType.SEQUENCE,
        )

    def rebuildTreeStructure(
        self,
        current_structure: dict[str, str | None],
        messages: Sequence[Message],
        from_node_id: uuid.UUID | None = None,
        active_leaf_id: uuid.UUID | None = None,
    ) -> tuple[dict[str, str | None], uuid.UUID]:
        new_structure = current_structure.copy()
        if from_node_id is not None:
            parent_id_str = str(from_node_id)
            if parent_id_str not in new_structure:
                raise ValueError(
                    f"from_node_id {from_node_id} not found in current tree structure."
                )
        elif active_leaf_id is not None:
            parent_id_str = str(active_leaf_id)
            if parent_id_str not in new_structure:
                raise ValueError(
                    f"active_leaf_id {active_leaf_id} not found in current tree structure."
                )
        else:
            parent_id_str = None

        prev_message_id = parent_id_str
        for msg in messages:
            msg_id = str(msg.uuid)
            new_structure[msg_id] = prev_message_id
            prev_message_id = msg_id
        if prev_message_id is None:
            raise ValueError("No messages to add to the tree structure.")
        return new_structure, uuid.UUID(prev_message_id)

    # create a new conversation with given messages if conversation_id is None,
    # otherwise append messages to existing conversation
    # with cache update to keep cache and db consistent
    async def _storeConversationMessagesWithCache(
        self,
        is_new_conversation: bool,
        conversation_uid: uuid.UUID,
        project_id: int,
        serialized_msgs: Sequence[Message],
        conversation_type: ConversationType,
        extra_metadata: dict | None = None,
        from_node_id: uuid.UUID | None = None,
    ) -> Result[
        None,
        ConversationNotFoundError
        | InvalidConversationTypeError
        | InternalServiceError,
    ]:
        async with self.session_manager.get_session() as session:
            if is_new_conversation:
                tree_structure, active_leaf_id = self.rebuildTreeStructure(
                    current_structure={},
                    messages=serialized_msgs,
                    from_node_id=from_node_id,
                )
                conversation = Conversation(
                    uuid=conversation_uid,
                    project_id=project_id,
                    extra_metadata=extra_metadata,
                    conversation_type=conversation_type,
                    tree_structure=tree_structure,
                    active_leaf_message_id=active_leaf_id,
                )
                session.add(conversation)
                await session.flush()
                conversation_id = conversation.id
            else:
                metadata = (
                    await self.conversation_repo.getConversationMetadataByUUID(
                        session, conversation_uid, project_id, for_="update"
                    )
                )
                if metadata is None:
                    return Err(ConversationNotFoundError())
                conversation_id = metadata["conversation_id"]
                if metadata["conversation_type"] != ConversationType.SEQUENCE:
                    return Err(InvalidConversationTypeError())
                tree_structure, active_leaf_id = self.rebuildTreeStructure(
                    current_structure=metadata["tree_structure"]
                    if metadata["tree_structure"] is not None
                    else {},
                    messages=serialized_msgs,
                    from_node_id=from_node_id,
                    active_leaf_id=metadata["active_leaf_message_id"],
                )
                updated_metadata = await self.conversation_repo.updateConversationTreeStructureByUUID(
                    session,
                    conversation_uuid=conversation_uid,
                    project_id=project_id,
                    tree_structure=tree_structure,
                    active_leaf_message_id=active_leaf_id,
                )
                if updated_metadata is None:
                    return Err(
                        InternalServiceError()
                    )  # this should not happen as we have locked the conversation row, just in case to prevent data inconsistency

            if len(serialized_msgs) > 0:
                for msg in serialized_msgs:
                    msg.conversation_id = conversation_id
                session.add_all(serialized_msgs)
                await session.flush()
            await session.commit()

        if len(serialized_msgs) > 0:
            await self.addConversationMessagesCache(
                conversation_uid, serialized_msgs
            )
        return Ok(None)

    async def createConversation(
        self,
        project_id: int,
        extra_metadata: dict | None,
        messages: Sequence[RequestMessage] | None,
    ) -> Result[
        uuid.UUID,
        ConversationNotFoundError
        | InvalidConversationTypeError
        | InternalServiceError,
    ]:
        conversation_uid = uuid7()
        res = await self._storeConversationMessagesWithCache(
            is_new_conversation=True,
            conversation_uid=conversation_uid,
            project_id=project_id,
            extra_metadata=extra_metadata,
            serialized_msgs=[
                Message(
                    conversation_id=-1,
                    payload=msg.payload,
                    timestamp=msg.timestamp,
                    extra_metadata=msg.extra_metadata,
                    run_id=msg.run_id,
                )
                for msg in messages
            ]
            if messages is not None
            else [],
            conversation_type=ConversationType.TREE,
        )
        if res.status == ResultStatus.Err:
            return res.into()
        return Ok(conversation_uid)


class TreeConversationWithSerializerService[T](TreeConversationService):
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
            offset=0,
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
        await self._storeConversationMessagesWithCache(
            is_new_conversation=is_new_conversation,
            conversation_uid=conversation_uid,
            project_id=project_id,
            serialized_msgs=serialized_msgs,
            conversation_type=ConversationType.TREE,
        )
