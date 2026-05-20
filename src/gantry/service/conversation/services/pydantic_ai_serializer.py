from gantry.service.conversation.types import SerializedSequenceContentPart

from ..types import (
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
from ..models import (
    Message,
)
from .serializer import Serializer
from ...file_storage.services import FileStorageService

import uuid
from typing import Sequence, cast
from datetime import UTC, datetime

from pyrusult import Err
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


class PydanticAISerializer(Serializer[ModelMessage]):
    def __init__(
        self,
        file_service: FileStorageService,
    ) -> None:
        self.file_service = file_service

    def serializeSequenceContentPart(
        self, contents: Sequence[UserContent]
    ) -> SerializedSequenceContentPart:
        """Serialize a sequence of contents into a storable format."""
        return {
            "type": "sequence",
            "data": [
                result
                for item in contents
                if (result := self.serializeContentPart(item)) is not None
            ],
        }

    def serializeContentPart(
        self, content: str | UserContent
    ) -> SerializedContentPart | None:
        """Serialize content into a storable format."""
        if isinstance(content, str):
            return {
                "type": "text",
                "data": content,
            }
        elif isinstance(content, (ImageUrl, AudioUrl, DocumentUrl, VideoUrl)):
            file_type = (
                FileType.IMAGE
                if isinstance(content, ImageUrl)
                else FileType.AUDIO
                if isinstance(content, AudioUrl)
                else FileType.VIDEO
                if isinstance(content, VideoUrl)
                else FileType.DOCUMENT
            )
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
                    "file_type": file_type,
                    "mime_type": content.media_type,
                }
        elif isinstance(content, BinaryContent):
            if (
                content.vendor_metadata
                and content.vendor_metadata["file_id"]
                and content.vendor_metadata.get("file_type")
            ):
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

    async def deserializePartContent(
        self, content: SerializedContent, project_id: int
    ) -> str | list[UserContent] | None:
        """Deserialize content from its serialized form."""
        if content["type"] == "text":
            return content["data"]
        elif content["type"] == "sequence":
            parts: list[str | UserContent] = []
            for item in content["data"]:
                deserialized_item = await self.deserializePartContent(
                    item, project_id
                )
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
            res = await self.file_service.getFileInfoAndUrl(
                uuid.UUID(file_id), project_id
            )
            if isinstance(res, Err):
                return None
            file_url, metadata = res.unwrap()
            mime_type = metadata["mime_type"]
            if content["file_type"] == FileType.VIDEO:
                return [
                    VideoUrl(
                        url=file_url,
                        media_type=mime_type,
                        vendor_metadata={"file_id": file_id},
                    )
                ]
            elif content["file_type"] == FileType.IMAGE:
                return [
                    ImageUrl(
                        url=file_url,
                        media_type=mime_type,
                        vendor_metadata={"file_id": file_id},
                    )
                ]
            elif content["file_type"] == FileType.AUDIO:
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

    async def serializeConversationMessages(
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
                        self.serializeContentPart(part.content)
                        if not isinstance(part.content, Sequence)
                        else self.serializeSequenceContentPart(part.content)
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
                payload={
                    "parts": parts,
                    "kind": msg.kind,
                },
                timestamp=msg.timestamp.astimezone(UTC).replace(tzinfo=None)
                if msg.timestamp
                else datetime.now(UTC).replace(tzinfo=None),
                extra_metadata={},
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
                payload={
                    "parts": parts,
                    "kind": msg.kind,
                },
                timestamp=msg.timestamp.astimezone(UTC).replace(tzinfo=None),
                run_id=msg.run_id,
                extra_metadata={
                    "model_name": msg.model_name,
                },
            )
        raise ValueError("Unsupported message kind")

    async def deserializeConversationMessages(
        self, message: Message, project_id: int
    ) -> ModelMessage:
        """Deserialize a stored Message into a ModelMessage."""
        payload = message.payload
        if (
            not isinstance(payload, dict)
            or "kind" not in payload
            or "parts" not in payload
        ):
            raise ValueError("Invalid message payload format")
        if payload["kind"] == "request":
            parts = []
            for part in payload["parts"]:
                if part["part_kind"] == "user-prompt":
                    part = cast(SerializedRequestUserPromptMessagePart, part)
                    content = await self.deserializePartContent(
                        part["content"], project_id
                    )
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
                timestamp=message.timestamp if message.timestamp else None,
                run_id=message.run_id,
            )
        if payload["kind"] == "response":
            parts = []
            for part in payload["parts"]:
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
                model_name=message.extra_metadata.get("model_name")
                if message.extra_metadata
                else None,
                timestamp=message.timestamp,
                run_id=message.run_id,
            )
        raise ValueError("Unsupported message kind")
