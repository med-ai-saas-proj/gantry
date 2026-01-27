from src.db.session import AsyncSessionManager
from src.management.api_keys.entities import ApiKeyInfo
from src.service.utils.conversation.models import (
    Message,
    MessagePart,
    Conversation,
)
from src.service.utils.conversation.repository import ConversationRepository

import json
import uuid
from typing import Sequence, Awaitable, cast
from datetime import UTC, datetime, timezone

from pydantic_ai import (
    TextPart,
    ModelMessage,
    ModelRequest,
    ThinkingPart,
    ToolCallPart,
    ModelResponse,
    ToolReturnPart,
    UserPromptPart,
    RetryPromptPart,
    BuiltinToolCallPart,
    BuiltinToolReturnPart,
    ModelMessagesTypeAdapter,
)
from pydantic_core import to_jsonable_python
from redis.asyncio import Redis


class ConversationService:
    def __init__(self,
                 session_manager: AsyncSessionManager,
                 conversation_repo: ConversationRepository,
                 redis_client: Redis
                 ) -> None:
        self.redis_client = redis_client
        self.session_manager = session_manager
        self.conversation_repo = conversation_repo

    async def get_conversation_id(
        self,
        conversation_uid: str,
        api_key_info: ApiKeyInfo
    ) -> int:
        async with self.session_manager.get_session() as session:
            conversation_id = await self.conversation_repo.get_conversation_id(
                session, uuid.UUID(conversation_uid), api_key_info["project_id"]
            )
            if conversation_id is None:
                raise ValueError("Conversation not found")
            return conversation_id

    def serialize_conversation_messages(
        self,
        conversation_id: int,
        msg: ModelMessage) -> Message:
        if msg.kind == "request":
            parts: list[MessagePart] = []
            for part in msg.parts:
                if part.part_kind == 'system-prompt':
                    continue
                elif part.part_kind == "user-prompt":
                    parts.append({
                        "part_kind": part.part_kind,
                        "content": part.content,
                        "timestamp": part.timestamp.isoformat(),
                    })
                elif part.part_kind == "retry-prompt":
                    parts.append({
                        "part_kind": part.part_kind,
                        "content": part.content,
                        "timestamp": part.timestamp.isoformat(),
                        "tool_call_id": part.tool_call_id,
                        "tool_name": part.tool_name,
                    })
                elif part.part_kind == "tool-return":
                    parts.append({
                        "part_kind": part.part_kind,
                        "content": part.content,
                        "timestamp": part.timestamp.isoformat(),
                        "tool_call_id": part.tool_call_id,
                        "tool_name": part.tool_name,
                        "metadata": part.metadata,
                    })
            return Message(
                conversation_id=conversation_id,
                kind=msg.kind,
                parts=parts,
                timestamp=msg.timestamp.isoformat()
                 if msg.timestamp else None,
                model_name=None,
                run_id=msg.run_id,
            )
        if msg.kind == "response":
            parts = []
            for part in msg.parts:
                if part.part_kind == "file":
                    continue # Skip file parts
                elif part.part_kind == "text":
                    parts.append({
                        "part_kind": part.part_kind,
                        "content": part.content,
                        "provider_details": part.provider_details,
                        "id": part.id
                    })
                elif part.part_kind == "thinking":
                    parts.append({
                        "part_kind": part.part_kind,
                        "content": part.content,
                        "provider_details": part.provider_details,
                        "id": part.id,
                        "provider_name": part.provider_name,
                        "signature": part.signature,
                    })
                elif part.part_kind == "tool-call":
                    parts.append({
                        "part_kind": part.part_kind,
                        "args": part.args,
                        "provider_details": part.provider_details,
                        "id": part.id,
                        "tool_call_id": part.tool_call_id,
                        "tool_name": part.tool_name,
                    })
                elif part.part_kind == "builtin-tool-call":
                    parts.append({
                        "part_kind": part.part_kind,
                        "args": part.args,
                        "provider_details": part.provider_details,
                        "provider_name": part.provider_name,
                        "id": part.id,
                        "tool_call_id": part.tool_call_id,
                        "tool_name": part.tool_name,
                    })
                elif part.part_kind == "builtin-tool-return":
                    parts.append({
                        "part_kind": part.part_kind,
                        "content": part.content,
                        "provider_details": part.provider_details,
                        "tool_call_id": part.tool_call_id,
                        "tool_name": part.tool_name,
                        "metadata": part.metadata,
                        "timestamp": part.timestamp.isoformat(),
                        "provider_name": part.provider_name,
                    })
            return Message(
                conversation_id=conversation_id,
                kind=msg.kind,
                model_name=msg.model_name,
                parts=parts,
                timestamp=msg.timestamp.isoformat(),
                run_id=msg.run_id,
            )

    def deserialize_conversation_messages(
        self,
        message: Message) -> ModelMessage:
        if message.kind == "request":
            parts = []
            for part in message.parts:
                if part["part_kind"] == "user-prompt":
                    parts.append(UserPromptPart(
                        content=part["content"],
                        timestamp=datetime.fromisoformat(part.get("timestamp")),
                    ))
                elif part["part_kind"] == "retry-prompt":
                    parts.append(RetryPromptPart(
                        content=part["content"],
                        timestamp=datetime.fromisoformat(part.get("timestamp")),
                        tool_call_id=part.get("tool_call_id"),
                        tool_name=part.get("tool_name"),
                    ))
                elif part["part_kind"] == "tool-return":
                    parts.append(ToolReturnPart(
                        content=part["content"],
                        timestamp=datetime.fromisoformat(part.get("timestamp")),
                        tool_call_id=part.get("tool_call_id"),
                        tool_name=part.get("tool_name"),
                        metadata=part.get("metadata"),
                    ))
            return ModelRequest(
                parts=parts,
                timestamp=datetime.fromisoformat(message.timestamp),
                run_id=message.run_id,
            )
        if message.kind == "response":
            parts = []
            for part in message.parts:
                if part["part_kind"] == "text":
                    parts.append(TextPart(
                        content=part["content"],
                        provider_details=part.get("provider_details"),
                        id=part.get("id"),
                    ))
                elif part["part_kind"] == "thinking":
                    parts.append(ThinkingPart(
                        content=part["content"],
                        provider_details=part.get("provider_details"),
                        id=part.get("id"),
                        provider_name=part.get("provider_name"),
                        signature=part.get("signature"),
                    ))
                elif part["part_kind"] == "tool-call":
                    parts.append(ToolCallPart(
                        args=part["args"],
                        provider_details=part.get("provider_details"),
                        id=part.get("id"),
                        tool_call_id=part.get("tool_call_id"),
                        tool_name=part.get("tool_name"),
                    ))
                elif part["part_kind"] == "builtin-tool-call":
                    parts.append(BuiltinToolCallPart(
                        args=part["args"],
                        provider_details=part.get("provider_details"),
                        provider_name=part.get("provider_name"),
                        id=part.get("id"),
                        tool_call_id=part.get("tool_call_id"),
                        tool_name=part.get("tool_name"),
                    ))
                elif part["part_kind"] == "builtin-tool-return":
                    parts.append(BuiltinToolReturnPart(
                        content=part["content"],
                        provider_details=part.get("provider_details"),
                        tool_call_id=part.get("tool_call_id"),
                        tool_name=part.get("tool_name"),
                        metadata=part.get("metadata"),
                        timestamp=datetime.fromisoformat(part.get("timestamp")),
                        provider_name=part.get("provider_name"),
                    ))
            return ModelResponse(
                parts=parts,
                model_name=message.model_name,
                timestamp=datetime.fromisoformat(message.timestamp),
                run_id=message.run_id,
            )

    async def get_conversation_message(self,
                                    conversation_id: int,
                                       conversation_uid: str) -> Sequence[ModelMessage]:
        # cached_msgs = await cast(Awaitable[list[str]], self.redis_client.lrange(conversation_uid, 0, -1))
        # if cached_msgs:
        #     model_msgs = []
        #     for msg in cached_msgs:
        #         msgs = ModelMessagesTypeAdapter.validate_json(msg)
        #         model_msgs.extend(msgs)
        #     return model_msgs

        async with self.session_manager.get_session() as session:
            serialized_msgs = await self.conversation_repo.get_messages_by_conversation_id(
                session, conversation_id
            )
            msgs = [self.deserialize_conversation_messages(msg) for msg in serialized_msgs]
            for msg in msgs:
                print(
                    "Deserialized message:", msg.kind, msg.timestamp, msg.run_id, msg.parts
                )
            return msgs


    async def store_conversation(self,
                                 conversation_id: int | None,
                                 conversation_uid: str,
                                 project_id: int,
                                 msgs: Sequence[ModelMessage]
                                 ) -> None:

        async with self.session_manager.get_session() as session:
            if conversation_id is None:
                conversation = Conversation(
                    title=None,
                    uuid=uuid.UUID(conversation_uid),
                    project_id=project_id
                )
                session.add(conversation)
                await session.commit()
                await session.refresh(conversation)
                conversation_id = conversation.id
            serialized_msgs = [
                self.serialize_conversation_messages(
                    conversation_id=conversation_id,
                    msg=msg
                ) for msg in msgs
            ]
            # await cast(Awaitable[int], self.redis_client.rpush(conversation_uid, json.dumps(to_jsonable_python(msgs))))
            session.add_all(serialized_msgs)
            await session.commit()
