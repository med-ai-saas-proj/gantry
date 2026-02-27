from src.db.session import AsyncSessionManager
from src.shared.custom_types.error_exception import RecoverableError

from .types import (
    FileType,
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
from .settings import ConversationSettings
from .repository import ConversationRepository
from ..file_storage.services import FileStorageService

import json
import uuid
import asyncio
from typing import Sequence, Awaitable, cast
from datetime import UTC, date, datetime
from dataclasses import asdict

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
    BinaryContent,
    ModelResponse,
    ToolReturnPart,
    UserPromptPart,
    RetryPromptPart,
    BuiltinToolCallPart,
    BuiltinToolReturnPart,
)
from safe_result import Ok, Err, Result
from redis.asyncio import Redis


class ConversationNotFoundError(RecoverableError):
    """Raised when a conversation is not found."""

    status = 404
    code = "conversation_not_found"
    title = "Conversation not found"
    detail = "The specified conversation does not exist or is not accessible with the provided API key"


class ConversationService:
    def __init__(
        self,
        session_manager: AsyncSessionManager,
        conversation_repo: ConversationRepository,
        file_service: FileStorageService,
        redis_client: Redis,
        setting: ConversationSettings
    ) -> None:
        """Initialize ConversationService."""
        self.redis_client = redis_client
        self.session_manager = session_manager
        self.conversation_repo = conversation_repo
        self.file_service = file_service
        self.setting = setting

    async def get_conversation_id(
        self, conversation_uid: uuid.UUID, project_id: int
    ) -> Result[int, ConversationNotFoundError]:
        """Get conversation ID by its UID and project ID."""
        async with self.session_manager.get_session() as session:
            conversation_id = await self.conversation_repo.get_conversation_id(
                session, conversation_uid, project_id
            )
            if conversation_id is None:
                return Err(ConversationNotFoundError())
            return Ok(conversation_id)

    def serialize_sequence_content(
        self, contents: Sequence[UserContent]
    ) -> SerializedSequenceContentPart:
        """Serialize a sequence of contents into a storable format."""
        return {
            "type": "sequence",
            "data": [
                result
                for item in contents
                if (result := self.serialize_part_content(item)) is not None
            ],
        }

    def serialize_part_content(
        self, content: str | UserContent
    ) -> SerializedContentPart | None:
        """Serialize content into a storable format."""
        if isinstance(content, str):
            return {
                "type": "text",
                "data": content,
            }
        elif isinstance(content, (ImageUrl, AudioUrl, DocumentUrl, VideoUrl)):
            file_type = (FileType.IMAGE
                    if isinstance(content, ImageUrl)
                    else FileType.AUDIO
                    if isinstance(content, AudioUrl)
                    else FileType.VIDEO
                    if isinstance(content, VideoUrl)
                    else FileType.DOCUMENT)
            if content.vendor_metadata and content.vendor_metadata["file_id"]:
                return {
                    "type": "file",
                    "file_id": str(content.vendor_metadata["file_id"]),
                    "file_type": file_type,
                }
            else:
                return {
                    "type": "file_url",
                    "url": content.url,  # assume url holds file id if vendor_metadata is missing
                    "file_type": file_type
                }
        elif isinstance(content, BinaryContent):
            if (content.vendor_metadata
                    and content.vendor_metadata["file_id"]
                    and content.vendor_metadata.get("file_type")):
                return {
                    "type": "file",
                    "file_id": str(content.vendor_metadata["file_id"]),
                    "file_type": content.vendor_metadata["file_type"],
                }
            else:
                # should not happen as BinaryContent must have file_id in vendor_metadata, but handle just in case
                raise ValueError(
                    "BinaryContent missing file_id in vendor_metadata"
                )
        else:
            # maybe CachePoint
            return None

    async def deserialize_part_content(
        self, content: SerializedContent
    ) -> str | list[UserContent] | None:
        """Deserialize content from its serialized form."""
        if content["type"] == "text":
            return content["data"]
        elif content["type"] == "sequence":
            parts = []
            for item in content["data"]:
                deserialized_item = await self.deserialize_part_content(item)
                if deserialized_item is None:
                    continue
                if isinstance(deserialized_item, list):
                    parts.extend(deserialized_item)
                else:
                    parts.append(deserialized_item)
            if len(parts) == 0:
                return None
            return parts
        elif content["type"] == "file":
            file_id = content["file_id"]
            res = (
                await self.file_service.get_file_metadata_and_url(
                    uuid.UUID(file_id)
                )
            )
            if isinstance(res, Err):
                return None
            file_url, metadata = res.unwrap()
            mime_type = metadata["mime_type"]
            if content['file_type'] == FileType.VIDEO:
                return [
                    VideoUrl(
                        url=file_url,
                        media_type=mime_type,
                        vendor_metadata={"file_id": file_id},
                    )
                ]
            elif content['file_type'] == FileType.IMAGE:
                return [
                    ImageUrl(
                        url=file_url,
                        media_type=mime_type,
                        vendor_metadata={"file_id": file_id},
                    )
                ]
            elif content['file_type'] == FileType.AUDIO:
                return [
                    AudioUrl(
                        url=file_url,
                        media_type=mime_type,
                        vendor_metadata={"file_id": file_id},
                    )
                ]
            else:
                return [
                    DocumentUrl(
                        url=file_url,
                        media_type=mime_type,
                        vendor_metadata={"file_id": file_id},
                    )
                ]
        elif content["type"] == "file_url":
            url = content["url"]
            file_type = content["file_type"]
            if file_type == FileType.VIDEO:
                return [VideoUrl(url=url)]
            elif file_type == FileType.IMAGE:
                return [ImageUrl(url=url)]
            elif file_type == FileType.AUDIO:
                return [AudioUrl(url=url)]
            else:
                return [DocumentUrl(url=url)]
        else:
            # should not happen as we only have text and file content types, but handle just in case
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
                    content = (
                        self.serialize_part_content(part.content)
                        if not isinstance(part.content, Sequence)
                        else self.serialize_sequence_content(part.content)
                    )
                    if content is not None:
                        parts.append(
                            {
                                "part_kind": part.part_kind,
                                "content": content,
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
                timestamp=msg.timestamp.astimezone(UTC).replace(tzinfo=None),
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
                timestamp=msg.timestamp.astimezone(UTC).replace(tzinfo=None),
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
                    content = await self.deserialize_part_content(part["content"])
                    if content is not None:
                        parts.append(
                            UserPromptPart(
                                content=content,
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
                timestamp=message.timestamp
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
                timestamp= message.timestamp,
                run_id=message.run_id,
            )
        raise ValueError("Unsupported message kind")

    async def getConversationMessageByUuid(
        self,
        conversation_uid: uuid.UUID,
        project_id: int
    )-> Result[Sequence[Message], ConversationNotFoundError]:
        async with self.session_manager.get_session() as session:
            conversation_id = await self.conversation_repo.get_conversation_id(
                session, conversation_uid, project_id
            )
            if conversation_id is None:
                return Err(ConversationNotFoundError())
        messages = await self._getConversationMessage(conversation_id, conversation_uid)
        return Ok(messages)

    async def _getConversationMessage(self,
                                      conversation_id: int,
                                      conversation_uid: uuid.UUID
                                      ) -> Sequence[Message]:
        cached_msgs = await cast(Awaitable[list[str]],
                                 self.redis_client.lrange(f"conversation_cache:{conversation_uid}", 0, -1))
        if cached_msgs:
            return [Message.parse_raw(json.loads(msg)) for msg in cached_msgs]
        else:
            async with self.session_manager.get_session() as session:
                msgs = await self.conversation_repo.get_messages_by_conversation_id(
                        session, conversation_id
                    )
                session.expunge_all()
            await self._replaceCacheConversationMessages(conversation_uid, msgs)
            return msgs

    async def getAndDeserializeConversationMessage(
        self,
        conversation_id: int,
        conversation_uid: uuid.UUID,
    ) -> Sequence[ModelMessage]:
        serialized_msgs = await self._getConversationMessage(conversation_id, conversation_uid)
        tasks = [
            self.deserialize_conversation_messages(msg)
            for msg in serialized_msgs
        ]
        msgs = await asyncio.gather(*tasks)
        return msgs

    async def serializeAndStoreConversation(
        self,
        conversation_id: int | None,
        conversation_uid: uuid.UUID,
        project_id: int,
        msgs: Sequence[ModelMessage],
    ) -> None:
        serialized_msgs = [
            self.serialize_conversation_messages(conversation_id=-1, msg=msg)
            for msg in msgs
        ]
        await self._storeConversationMessage(
            conversation_id, conversation_uid, project_id, serialized_msgs
        )

    async def storeConversationMessageByUuid(
        self,
        conversation_uid: uuid.UUID,
        project_id: int,
        msgs: Sequence[Message],
    ) -> None:
        async with self.session_manager.get_session() as session:
            conversation_id = await self.conversation_repo.get_conversation_id(
                session, conversation_uid, project_id
            )
        await self._storeConversationMessage(
            conversation_id, conversation_uid, project_id, msgs
        )

    async def _storeConversationMessage(
        self,
        conversation_id: int | None,
        conversation_uid: uuid.UUID,
        project_id: int,
        serialized_msgs: Sequence[Message],
    ):
        if conversation_id is None:
            async with self.session_manager.get_session() as session:
                conversation = Conversation(
                    title=None,
                    uuid=conversation_uid,
                    project_id=project_id,
                )
                session.add(conversation)
                await session.flush()
                conversation_id = conversation.id
                await session.commit()

        for msg in serialized_msgs:
            msg.conversation_id = conversation_id

        async with self.session_manager.get_session() as session:
            session.add_all(serialized_msgs)
            await session.flush()
            await session.commit()
        await self._addCacheConversationMessages(conversation_uid, serialized_msgs)

    async def _replaceCacheConversationMessages(self,
         conversation_uid: uuid.UUID,
         msgs: Sequence[Message]):
        async with self.redis_client.pipeline(
            transaction=True
        ) as pipe:
            await cast(Awaitable[None],
               pipe.delete(f"conversation_cache:{conversation_uid}"))
            await cast(Awaitable[int],
               pipe.rpush(
                f"conversation_cache:{conversation_uid}",
                *[json.dumps(asdict(msg),
                    default=_json_serial) for msg in msgs]
            ))
            await cast(Awaitable[None],
               pipe.expire(
                f"conversation_cache:{conversation_uid}",
                self.setting.cache_ttl
            ))
            await pipe.execute()

    async def _addCacheConversationMessages(self,
         conversation_uid: uuid.UUID,
         msgs: Sequence[Message]):
        async with self.redis_client.pipeline() as pipe:
            await cast(Awaitable[int],
               pipe.rpush(
                f"conversation_cache:{conversation_uid}",
                *[json.dumps(asdict(msg),
                    default=_json_serial) for msg in msgs]
            ))
            await cast(Awaitable[None],
               pipe.expire(
                f"conversation_cache:{conversation_uid}",
                self.setting.cache_ttl
            ))
            await pipe.execute()


def _json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")
