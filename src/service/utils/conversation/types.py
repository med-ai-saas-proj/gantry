from datetime import datetime
import enum
import uuid


from typing import Any, Literal, Sequence, TypedDict

from pydantic_core import ErrorDetails


class FileType(enum.Enum):
    """Enumeration of supported file types."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"


class SerializedTextContentPart(TypedDict):
    """Serialized representation of a message part."""

    type: Literal["text"]
    data: str


class SerializedFileContentPart(TypedDict):
    """Serialized representation of a file message part."""

    type: Literal["file"]
    file_id: str
    file_type: FileType


class SerializedFileUrlContentPart(TypedDict):
    """Serialized representation of a file URL message part."""

    type: Literal["file_url"]
    url: str
    file_type: FileType


SerializedContentPart = (
    SerializedTextContentPart
    | SerializedFileContentPart
    | SerializedFileUrlContentPart
)


class SerializedSequenceContentPart(TypedDict):
    """Serialized representation of a sequence of content parts."""

    type: Literal["sequence"]
    data: list[SerializedContentPart]


SerializedContent = SerializedContentPart | SerializedSequenceContentPart


class SerializedMessagePart(TypedDict):
    """Serialized representation of a message."""

    part_kind: str


class SerializedRequestUserPromptMessagePart(SerializedMessagePart):
    """Serialized representation of a user prompt message part."""

    content: SerializedContent
    timestamp: str


class SerializedRequestRetryPromptMessagePart(SerializedMessagePart):
    """Serialized representation of a retry prompt message part."""

    content: str | list[ErrorDetails]
    tool_name: str | None
    tool_call_id: str
    timestamp: str


class SerializedRequestToolReturnMessagePart(SerializedMessagePart):
    """Serialized representation of a tool return message part."""

    content: Any
    tool_name: str
    tool_call_id: str
    metadata: Any
    timestamp: str


class SerializedResponseMessagePart(SerializedMessagePart):
    """Serialized representation of a text response message part."""

    id: str | None


class SerializedResponseTextMessagePart(SerializedResponseMessagePart):
    """Serialized representation of a text response message part."""

    content: str
    provider_details: dict[str, Any] | None


class SerializedResponseThinkingMessagePart(SerializedResponseTextMessagePart):
    """Serialized representation of a thinking response message part."""

    provider_name: str | None
    signature: str | None


class SerializedResponseToolCallMessagePart(SerializedResponseMessagePart):
    """Serialized representation of a tool call response message part."""

    tool_name: str
    tool_call_id: str
    args: Any
    provider_details: dict[str, Any] | None


class SerializedResponseBuiltInToolCallMessagePart(
    SerializedResponseToolCallMessagePart
):
    """Serialized representation of a built-in tool call response message part."""

    provider_name: str | None


class SerializedResponseBuiltInToolResultMessagePart(SerializedMessagePart):
    """Serialized representation of a built-in tool result response message part."""

    content: Any
    tool_call_id: str
    tool_name: str
    metadata: Any
    timestamp: str
    provider_name: str | None
    provider_details: dict[str, Any] | None


MessagePart = (
    SerializedRequestUserPromptMessagePart
    | SerializedRequestRetryPromptMessagePart
    | SerializedRequestToolReturnMessagePart
    | SerializedResponseTextMessagePart
    | SerializedResponseThinkingMessagePart
    | SerializedResponseToolCallMessagePart
    | SerializedResponseBuiltInToolCallMessagePart
    | SerializedResponseBuiltInToolResultMessagePart
)


class FileUploadInfo(TypedDict):
    file_id: uuid.UUID
    file_data: bytes
    mime_type: str
    is_uploaded: bool


class ConversationMetadata(TypedDict):
    conversation_id: int
    conversation_uid: uuid.UUID
    project_id: int
    extra_metadata: dict | None
    created_at: datetime
