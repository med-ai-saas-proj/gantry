from src.db.session import AsyncSessionManager
from src.management.api_keys.entities import ApiKeyInfo
from src.service.utils.file_storage.services import FileStorageService

from .types import (
    MessagePart,
    SerializedContent,
    SerializedContentPart,
    SerializedSequenceContentPart,
    SerializedResponseTextMessagePart,
    SerializedResponseThinkingMessagePart,
    SerializedResponseToolCallMessagePart,
    SerializedRequestToolReturnMessagePart,
    SerializedRequestUserPromptMessagePart,
    SerializedRequestRetryPromptMessagePart,
    SerializedResponseBuiltInToolCallMessagePart,
    SerializedResponseBuiltInToolResultMessagePart,
)
from .models import (
    Message,
    Conversation,
)
from .repository import ConversationRepository
from ..file_storage.models import FileType

import uuid
import asyncio
from typing import Sequence, cast
from datetime import datetime

from pydantic_ai import (
    AudioUrl,
    ImageUrl,
    TextPart,
    VideoUrl,
    DocumentUrl,
    UserContent,
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
)
from redis.asyncio import Redis


class ConversationService:
    def __init__(
        self,
        session_manager: AsyncSessionManager,
        conversation_repo: ConversationRepository,
        file_service: FileStorageService,
        redis_client: Redis,
    ) -> None:
        """Initialize ConversationService."""
        self.redis_client = redis_client
        self.session_manager = session_manager
        self.conversation_repo = conversation_repo
        self.file_service = file_service

    async def get_conversation_id(
        self, conversation_uid: str, api_key_info: ApiKeyInfo
    ) -> int:
        """Get conversation ID by its UID and project ID."""
        async with self.session_manager.get_session() as session:
            conversation_id = await self.conversation_repo.get_conversation_id(
                session, uuid.UUID(conversation_uid), api_key_info["project_id"]
            )
            if conversation_id is None:
                raise ValueError("Conversation not found")
            return conversation_id

    def serialize_sequence_content(
        self, contents: Sequence[UserContent]
    ) -> SerializedSequenceContentPart:
        """Serialize a sequence of contents into a storable format."""
        return {
            "type": "sequence",
            "data": [self.serialize_part_content(item) for item in contents],
        }

    def serialize_part_content(
        self, content: str | UserContent
    ) -> SerializedContentPart:
        """Serialize content into a storable format."""
        if isinstance(content, str):
            return {
                "type": "text",
                "data": content,
            }
        elif isinstance(content, (ImageUrl, AudioUrl, DocumentUrl, VideoUrl)):
            if content.vendor_metadata and content.vendor_metadata["file_id"]:
                return {
                    "type": "file",
                    "file_id": content.vendor_metadata["file_id"],
                }
            else:
                return {
                    "type": "file_url",
                    "url": content.url,  # assume url holds file id if vendor_metadata is missing
                    "file_type": isinstance(content, ImageUrl)
                    and FileType.IMAGE
                    or isinstance(content, AudioUrl)
                    and FileType.AUDIO
                    or isinstance(content, DocumentUrl)
                    and FileType.DOCUMENT
                    or isinstance(content, VideoUrl)
                    and FileType.VIDEO
                    or FileType.GENERAL,
                }
        else:
            raise ValueError("Unsupported content type")

    async def deserialize_part_content(
        self, content: SerializedContent
    ) -> str | list[UserContent]:
        """Deserialize content from its serialized form."""
        if content["type"] == "text":
            return cast(str, content["data"])
        elif content["type"] == "sequence":
            parts = []
            for item in content["data"]:
                if isinstance(item, dict):
                    deserialized_item = self.deserialize_part_content(item)
                    if isinstance(deserialized_item, list):
                        parts.extend(deserialized_item)
                    else:
                        parts.append(deserialized_item)
                else:
                    parts.append(item)
            return parts
        elif content["type"] == "file":
            (
                file_url,
                metadata,
            ) = await self.file_service.get_file_metadata_and_url(
                uuid.UUID(content["file_id"])
            )
            if metadata["file_type"] == FileType.VIDEO:
                return [
                    VideoUrl(
                        url=file_url,
                        vendor_metadata={"file_id": content["file_id"]},
                    )
                ]
            elif metadata["file_type"] == FileType.IMAGE:
                return [
                    ImageUrl(
                        url=file_url,
                        vendor_metadata={"file_id": content["file_id"]},
                    )
                ]
            elif metadata["file_type"] == FileType.AUDIO:
                return [
                    AudioUrl(
                        url=file_url,
                        vendor_metadata={"file_id": content["file_id"]},
                    )
                ]
            else:
                return [
                    DocumentUrl(
                        url=file_url,
                        vendor_metadata={"file_id": content["file_id"]},
                    )
                ]
        elif content["type"] == "file_url":
            if content["file_type"] == FileType.VIDEO:
                return [VideoUrl(url=content["url"])]
            elif content["file_type"] == FileType.IMAGE:
                return [ImageUrl(url=content["url"])]
            elif content["file_type"] == FileType.AUDIO:
                return [AudioUrl(url=content["url"])]
            else:
                return [DocumentUrl(url=content["url"])]
        raise ValueError("Unsupported content type")

    def serialize_conversation_messages(
        self, conversation_id: int, msg: ModelMessage
    ) -> Message:
        """Serialize a ModelMessage into a storable Message."""
        if msg.kind == "request":
            parts: list[MessagePart] = []
            for part in msg.parts:
                if part.part_kind == "system-prompt":
                    continue
                elif part.part_kind == "user-prompt":
                    parts.append(
                        {
                            "part_kind": part.part_kind,
                            "content": self.serialize_part_content(part.content)
                            if not isinstance(part.content, Sequence)
                            else self.serialize_sequence_content(part.content),
                            "timestamp": part.timestamp.isoformat(),
                        }
                    )
                elif part.part_kind == "retry-prompt":
                    parts.append(
                        {
                            "part_kind": part.part_kind,
                            "content": part.content,
                            "timestamp": part.timestamp.isoformat(),
                            "tool_call_id": part.tool_call_id,
                            "tool_name": part.tool_name,
                        }
                    )
                elif part.part_kind == "tool-return":
                    parts.append(
                        {
                            "part_kind": part.part_kind,
                            "content": part.content,
                            "timestamp": part.timestamp.isoformat(),
                            "tool_call_id": part.tool_call_id,
                            "tool_name": part.tool_name,
                            "metadata": part.metadata,
                        }
                    )
            return Message(
                conversation_id=conversation_id,
                kind=msg.kind,
                parts=parts,
                timestamp=msg.timestamp.isoformat() if msg.timestamp else None,
                model_name=None,
                run_id=msg.run_id,
            )
        if msg.kind == "response":
            parts = []
            for part in msg.parts:
                if part.part_kind == "file":
                    continue  # Skip file parts
                elif part.part_kind == "text":
                    parts.append(
                        {
                            "part_kind": part.part_kind,
                            "content": part.content,
                            "provider_details": part.provider_details,
                            "id": part.id,
                        }
                    )
                elif part.part_kind == "thinking":
                    parts.append(
                        {
                            "part_kind": part.part_kind,
                            "content": part.content,
                            "provider_details": part.provider_details,
                            "id": part.id,
                            "provider_name": part.provider_name,
                            "signature": part.signature,
                        }
                    )
                elif part.part_kind == "tool-call":
                    parts.append(
                        {
                            "part_kind": part.part_kind,
                            "args": part.args,
                            "provider_details": part.provider_details,
                            "id": part.id,
                            "tool_call_id": part.tool_call_id,
                            "tool_name": part.tool_name,
                        }
                    )
                elif part.part_kind == "builtin-tool-call":
                    parts.append(
                        {
                            "part_kind": part.part_kind,
                            "args": part.args,
                            "provider_details": part.provider_details,
                            "provider_name": part.provider_name,
                            "id": part.id,
                            "tool_call_id": part.tool_call_id,
                            "tool_name": part.tool_name,
                        }
                    )
                elif part.part_kind == "builtin-tool-return":
                    parts.append(
                        {
                            "part_kind": part.part_kind,
                            "content": part.content,
                            "tool_call_id": part.tool_call_id,
                            "tool_name": part.tool_name,
                            "metadata": part.metadata,
                            "timestamp": part.timestamp.isoformat(),
                            "provider_name": part.provider_name,
                            "provider_details": part.provider_details,
                        }
                    )
            return Message(
                conversation_id=conversation_id,
                kind=msg.kind,
                model_name=msg.model_name,
                parts=parts,
                timestamp=msg.timestamp.isoformat(),
                run_id=msg.run_id,
            )
        raise ValueError("Unsupported message kind")

    async def deserialize_conversation_messages(
        self, message: Message
    ) -> ModelMessage:
        """Deserialize a stored Message into a ModelMessage."""
        if message.kind == "request":
            parts = []
            for part in message.parts:
                if part["part_kind"] == "user-prompt":
                    part = cast(SerializedRequestUserPromptMessagePart, part)
                    parts.append(
                        UserPromptPart(
                            content=await self.deserialize_part_content(
                                part["content"]
                            ),
                            timestamp=datetime.fromisoformat(
                                part.get("timestamp")
                            ),
                        )
                    )
                elif part["part_kind"] == "retry-prompt":
                    part = cast(SerializedRequestRetryPromptMessagePart, part)
                    parts.append(
                        RetryPromptPart(
                            content=part["content"],
                            timestamp=datetime.fromisoformat(
                                part.get("timestamp")
                            ),
                            tool_call_id=part.get("tool_call_id"),
                            tool_name=part.get("tool_name"),
                        )
                    )
                elif part["part_kind"] == "tool-return":
                    part = cast(SerializedRequestToolReturnMessagePart, part)
                    parts.append(
                        ToolReturnPart(
                            content=part["content"],
                            timestamp=datetime.fromisoformat(
                                part.get("timestamp")
                            ),
                            tool_call_id=part.get("tool_call_id"),
                            tool_name=part.get("tool_name"),
                            metadata=part.get("metadata"),
                        )
                    )
            return ModelRequest(
                parts=parts,
                timestamp=datetime.fromisoformat(message.timestamp)
                if message.timestamp
                else None,
                run_id=message.run_id,
            )
        if message.kind == "response":
            parts = []
            for part in message.parts:
                if part["part_kind"] == "text":
                    part = cast(SerializedResponseTextMessagePart, part)
                    parts.append(
                        TextPart(
                            content=part["content"],
                            provider_details=part.get("provider_details"),
                            id=part.get("id"),
                        )
                    )
                elif part["part_kind"] == "thinking":
                    part = cast(SerializedResponseThinkingMessagePart, part)
                    parts.append(
                        ThinkingPart(
                            content=part["content"],
                            provider_details=part.get("provider_details"),
                            id=part.get("id"),
                            provider_name=part.get("provider_name"),
                            signature=part.get("signature"),
                        )
                    )
                elif part["part_kind"] == "tool-call":
                    part = cast(SerializedResponseToolCallMessagePart, part)
                    parts.append(
                        ToolCallPart(
                            args=part["args"],
                            provider_details=part.get("provider_details"),
                            id=part.get("id"),
                            tool_call_id=part.get("tool_call_id"),
                            tool_name=part.get("tool_name"),
                        )
                    )
                elif part["part_kind"] == "builtin-tool-call":
                    part = cast(
                        SerializedResponseBuiltInToolCallMessagePart, part
                    )
                    parts.append(
                        BuiltinToolCallPart(
                            args=part["args"],
                            provider_details=part.get("provider_details"),
                            provider_name=part.get("provider_name"),
                            id=part.get("id"),
                            tool_call_id=part.get("tool_call_id"),
                            tool_name=part.get("tool_name"),
                        )
                    )
                elif part["part_kind"] == "builtin-tool-return":
                    part = cast(
                        SerializedResponseBuiltInToolResultMessagePart, part
                    )
                    parts.append(
                        BuiltinToolReturnPart(
                            content=part["content"],
                            provider_details=part.get("provider_details"),
                            tool_call_id=part.get("tool_call_id"),
                            tool_name=part.get("tool_name"),
                            metadata=part.get("metadata"),
                            timestamp=datetime.fromisoformat(
                                part.get("timestamp")
                            ),
                            provider_name=part.get("provider_name"),
                        )
                    )
            return ModelResponse(
                parts=parts,
                model_name=message.model_name,
                timestamp=datetime.fromisoformat(cast(str, message.timestamp)),
                run_id=message.run_id,
            )
        raise ValueError("Unsupported message kind")

    async def get_conversation_message(
        self, conversation_id: int, conversation_uid: str
    ) -> Sequence[ModelMessage]:
        # cached_msgs = await cast(Awaitable[list[str]], self.redis_client.lrange(conversation_uid, 0, -1))
        # if cached_msgs:
        #     model_msgs = []
        #     for msg in cached_msgs:
        #         msgs = ModelMessagesTypeAdapter.validate_json(msg)
        #         model_msgs.extend(msgs)
        #     return model_msgs

        async with self.session_manager.get_session() as session:
            serialized_msgs = (
                await self.conversation_repo.get_messages_by_conversation_id(
                    session, conversation_id
                )
            )
            tasks = [
                self.deserialize_conversation_messages(msg)
                for msg in serialized_msgs
            ]
            msgs = await asyncio.gather(*tasks)
            for msg in msgs:
                print(
                    "Deserialized message:",
                    msg.kind,
                    msg.timestamp,
                    msg.run_id,
                    msg.parts,
                )
            return msgs

    async def store_conversation(
        self,
        conversation_id: int | None,
        conversation_uid: str,
        project_id: int,
        msgs: Sequence[ModelMessage],
    ) -> None:
        async with self.session_manager.get_session() as session:
            if conversation_id is None:
                conversation = Conversation(
                    title=None,
                    uuid=uuid.UUID(conversation_uid),
                    project_id=project_id,
                )
                session.add(conversation)
                await session.flush()
                conversation_id = conversation.id
            serialized_msgs = [
                self.serialize_conversation_messages(
                    conversation_id=conversation_id, msg=msg
                )
                for msg in msgs
            ]
            # await cast(Awaitable[int], self.redis_client.rpush(conversation_uid, json.dumps(to_jsonable_python(msgs))))
            session.add_all(serialized_msgs)
            await session.commit()
