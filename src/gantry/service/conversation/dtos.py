from .types import (
    SerializedResponseTextMessagePart,
    SerializedResponseThinkingMessagePart,
    SerializedResponseToolCallMessagePart,
    SerializedRequestToolReturnMessagePart,
    SerializedRequestUserPromptMessagePart,
    SerializedRequestRetryPromptMessagePart,
    SerializedResponseBuiltInToolCallMessagePart,
    SerializedResponseBuiltInToolResultMessagePart,
)

import uuid
from typing import Literal, Sequence
from datetime import datetime

from pydantic import BaseModel


RequestMessagePart = (
    SerializedRequestUserPromptMessagePart
    | SerializedRequestRetryPromptMessagePart
    | SerializedRequestToolReturnMessagePart
)

ResponseMessagePart = (
    SerializedResponseTextMessagePart
    | SerializedResponseThinkingMessagePart
    | SerializedResponseToolCallMessagePart
    | SerializedResponseBuiltInToolCallMessagePart
    | SerializedResponseBuiltInToolResultMessagePart
)


class ResponseMessage(BaseModel):
    """Represents a response message in a conversation."""

    model_config = {
        "from_attributes": True,
    }

    kind: Literal["response"]
    parts: list[ResponseMessagePart]

    # metadata fields
    model_name: str | None = None
    timestamp: datetime
    run_id: str | None = None


class RequestMessage(BaseModel):
    """Represents a request message in a conversation."""

    kind: Literal["request"]
    parts: list[RequestMessagePart]

    # metadata fields
    model_name: str | None = None
    timestamp: datetime
    run_id: str | None = None


class ResponseMessageResponse(ResponseMessage):
    message_uid: uuid.UUID


class RequestMessageResponse(RequestMessage):
    message_uid: uuid.UUID


class AddMessageRequest(BaseModel):
    """Represents a request to add a message to a conversation."""

    messages: Sequence[RequestMessage | ResponseMessage]


class CreateConversationRequest(BaseModel):
    """Represents a request to create a new conversation."""

    extra_metadata: dict | None = None
    messages: Sequence[RequestMessage | ResponseMessage] | None = None


class CreateConversationResponse(BaseModel):
    """Represents a response after creating a new conversation."""

    conversation_uid: uuid.UUID


class ConversationMetadataResponse(BaseModel):
    """Represents the metadata of a conversation."""

    conversation_uid: uuid.UUID
    project_id: int
    extra_metadata: dict | None = None
    created_at: datetime


class UpdateConversationMetadataRequest(BaseModel):
    """Represents a request to update a conversation."""

    extra_metadata: dict | None = None
