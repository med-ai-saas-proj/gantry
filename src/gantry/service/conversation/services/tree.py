from gantry.db.session import AsyncSessionManager
from gantry.shared.utils.uuid_utils import uuid7
from gantry.shared.custom_types.error_exception import (
    InvalidValueError,
    InternalServiceError,
)

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

import uuid
import asyncio
from typing import Literal, Sequence
from datetime import UTC

from pyrusult import Ok, Err, Result, ResultStatus
from redis.asyncio import Redis


ROOT_NODE_ID = str(
    uuid.UUID(int=0)
)  # a sentinel node id to represent the root of the tree


class TreeConversationService(ConversationService):
    """Implements a conversation service where messages are stored in a single sequence, and the entire sequence is retrieved for each request."""

    async def getConversationMessages(
        self,
        conversation_uid: uuid.UUID,
        project_id: int,
        limit: int = 20,
        order_by: Literal["asc", "desc"] = "asc",
        last_cursor: uuid.UUID | None = None,
        branch_node_id: uuid.UUID | None = None,
    ) -> Result[Sequence[Message], ConversationNotFoundError]:
        async with self.session_manager.get_session() as session:
            metadata = (
                await self.conversation_repo.getConversationMetadataByUUID(
                    session, conversation_uid, project_id
                )
            )
            if metadata is None:
                return Err(ConversationNotFoundError())
        return await self._getConversationMessagesWithCache(
            conversation_uid=conversation_uid,
            project_id=project_id,
            last_cursor=last_cursor,
            limit=limit,
            order_by=order_by,
            branch_node_id=branch_node_id,
        )

    async def _getConversationMessagesWithCache(
        self,
        conversation_uid: uuid.UUID,
        project_id: int,
        last_cursor: uuid.UUID | None = None,
        limit: int = 20,
        order_by: Literal["asc", "desc"] = "asc",
        branch_node_id: uuid.UUID | None = None,
    ) -> Result[Sequence[Message], ConversationNotFoundError]:
        async with self.session_manager.get_session() as session:
            metadata = (
                await self.conversation_repo.getConversationMetadataByUUID(
                    session, conversation_uid, project_id=project_id
                )
            )
            if metadata is None:
                return Err(ConversationNotFoundError())
        if metadata["conversation_type"] != ConversationType.TREE:
            raise InvalidConversationTypeError()
        tree_structure = (
            metadata["tree_structure"]
            if metadata["tree_structure"] is not None
            else {}
        )

        if (
            branch_node_id is not None
            and str(branch_node_id) not in tree_structure
        ):
            return Ok(
                []
            )  # if branch_node_id is provided but not found in the tree structure, return empty result as it may indicate client has reached the end of the conversation branch
        if last_cursor is not None and str(last_cursor) not in tree_structure:
            return Ok(
                []
            )  # if last_cursor is provided but not found in the tree structure, return empty result as it may indicate client has reached the end of the conversation history

        stack = []
        cur_node = None
        if branch_node_id is not None:
            cur_node = str(branch_node_id)
        else:
            cur_node = (
                str(metadata["active_leaf_message_id"])
                if metadata["active_leaf_message_id"] is not None
                else None
            )

        while cur_node is not None and cur_node != ROOT_NODE_ID:
            stack.append(cur_node)
            cur_node = tree_structure.get(cur_node)

        if order_by == "asc":
            stack.reverse()

        if last_cursor is not None:
            last_cursor_str = str(last_cursor)
            if last_cursor_str in stack:
                if last_cursor_str in stack:
                    cursor_idx = stack.index(last_cursor_str)
                    stack = stack[cursor_idx + 1 :]
            else:
                # if last_cursor is not found, return empty result as it may indicate client has reached the end of the conversation history
                return Ok([])

        stack = stack[:limit]

        if len(stack) == 0:
            return Ok([])

        messages = await self.getConversationMessagesByUuids(
            conversation_uid=conversation_uid,
            message_uids=[uuid.UUID(msg_id) for msg_id in stack],
            project_id=project_id,
        )
        messages_dict = {str(msg.uuid): msg for msg in messages}
        sorted_messages = [
            messages_dict[msg_id] for msg_id in stack if msg_id in messages_dict
        ]
        return Ok(sorted_messages)

    async def storeConversationMessages(
        self,
        conversation_uid: uuid.UUID,
        project_id: int,
        msgs: Sequence[RequestMessage],
        from_node_id: uuid.UUID | None = None,
    ) -> Result[
        None,
        ConversationNotFoundError
        | InvalidConversationTypeError
        | InvalidValueError
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
                    uuid=msg.message_uid,
                    conversation_id=-1,
                    payload=msg.payload,
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
            conversation_type=ConversationType.SEQUENCE,
            from_node_id=from_node_id,
        )

    def rebuildTreeStructure(
        self,
        current_structure: dict[str, str],  # <message_id, parent_message_id>
        new_messages: Sequence[Message],
        from_node_id: uuid.UUID | None = None,
        active_leaf_id: uuid.UUID | None = None,
    ) -> Result[tuple[dict[str, str], uuid.UUID], InvalidValueError]:
        new_structure = current_structure.copy()
        if from_node_id is not None:
            parent_id_str = str(from_node_id)
            if parent_id_str not in new_structure:
                return Err(
                    InvalidValueError(
                        message=f"from_node_id {from_node_id} not found in current tree structure."
                    )
                )
        elif active_leaf_id is not None:
            parent_id_str = str(active_leaf_id)
            if parent_id_str not in new_structure:
                return Err(
                    InvalidValueError(
                        message=f"active_leaf_id {active_leaf_id} not found in current tree structure."
                    )
                )
        else:
            parent_id_str = None

        prev_message_id = (
            parent_id_str if parent_id_str is not None else ROOT_NODE_ID
        )
        for msg in new_messages:
            msg_id = str(msg.uuid)
            new_structure[msg_id] = prev_message_id
            prev_message_id = msg_id
        return Ok((new_structure, uuid.UUID(prev_message_id)))

    def rebuildRelationshipsMap(
        self,
        current_map: dict[str, str],  # <message_id, next_message_id>
        new_messages: Sequence[Message],
        from_node_id: uuid.UUID | None = None,
    ) -> dict[str, str]:
        new_map = current_map.copy()
        cur_message_id = (
            str(from_node_id) if from_node_id is not None else ROOT_NODE_ID
        )
        for msg in new_messages:
            new_map[cur_message_id] = str(msg.uuid)
            cur_message_id = str(msg.uuid)
        return new_map

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
        | InvalidValueError
        | InternalServiceError,
    ]:
        async with self.session_manager.get_session() as session:
            if is_new_conversation:
                new_tree_res = self.rebuildTreeStructure(
                    current_structure={},
                    new_messages=serialized_msgs,
                )
                if new_tree_res.status == ResultStatus.Err:
                    return new_tree_res.into()
                new_tree_structure, new_active_leaf_id = new_tree_res.unwrap()
                conversation = Conversation(
                    uuid=conversation_uid,
                    project_id=project_id,
                    extra_metadata=extra_metadata,
                    conversation_type=conversation_type,
                    tree_structure=new_tree_structure,
                    active_leaf_message_id=new_active_leaf_id,
                    relationships_map={},
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
                if metadata["conversation_type"] != ConversationType.TREE:
                    return Err(InvalidConversationTypeError())
                new_tree_res = self.rebuildTreeStructure(
                    current_structure=metadata["tree_structure"]
                    if metadata["tree_structure"] is not None
                    else {},
                    new_messages=serialized_msgs,
                    from_node_id=from_node_id,
                    active_leaf_id=metadata["active_leaf_message_id"],
                )
                if new_tree_res.status == ResultStatus.Err:
                    return new_tree_res.into()
                new_tree_structure, new_active_leaf_id = new_tree_res.unwrap()
                new_relationships_map = self.rebuildRelationshipsMap(
                    current_map=metadata["relationships_map"]
                    if metadata["relationships_map"] is not None
                    else {},
                    new_messages=serialized_msgs,
                    from_node_id=from_node_id,
                )
                updated_metadata = await self.conversation_repo.updateConversationTreeStructureByUUID(
                    session,
                    conversation_uuid=conversation_uid,
                    project_id=project_id,
                    tree_structure=new_tree_structure,
                    active_leaf_message_id=new_active_leaf_id,
                    relationships_map=new_relationships_map,
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
        await self.redis_client.delete(
            ConversationService._conversation_cache_key(conversation_uid)
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
        | InvalidValueError
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
                    uuid=msg.message_uid,
                    conversation_id=-1,
                    payload=msg.payload,
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
        conversation_uid: uuid.UUID,
        project_id: int,
        limit: int = 20,
    ) -> Sequence[T]:
        serialized_msgs = (
            await self._getConversationMessagesWithCache(
                conversation_uid,
                last_cursor=None,
                limit=limit,
                order_by="desc",
                branch_node_id=None,
                project_id=project_id,
            )
        ).unwrap()
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
