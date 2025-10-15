"""This file contain definition of chat's database entities."""

from src.shared.entities.base import BaseEntity

from uuid import UUID
from typing import Literal, TypedDict
from datetime import datetime


class Conversation(BaseEntity):
    """**table_name**: `conversations`.

    Conversation id and metadata.

    `metadata`: key value pairs, limited to 16 pairs,
        max key len is 64, max value len is 512
    """

    pk: int
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    metadata: dict[str, str]


class ConversationNotDeleted(BaseEntity):
    """**view_name**: `conversations_not_deleted`.

    View conversation where deleted_at is NULL
    """

    pk: int
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, str]


class AIProvider(BaseEntity):
    """**table_name**: `ai_providers`, **only modify on new db version**.

    Contain information about AI service providers
    """

    pk: int
    name: str


class BaseAIModel(BaseEntity):
    """**table_name**: `base_ai_models`, **admin only**.

    Contain information about llm base models for Admin
    """

    pk: int
    name: str
    provider_pk: int
    model_id: str
    api_key: str
    rate_per_sec: int


class AIModel(BaseEntity):
    """**table_name**: `ai_models`.

    User's custom model. Matches migration table `custom_ai_models` and
    references the base model via `ai_model_pk`.
    """

    pk: int
    user_id: UUID | None
    name: str
    base_ai_model_pk: int
    instruction: str


class MessageRole(BaseEntity):
    """**table_name**: `message_roles`, **only modify on new db version**.

    Message role, should contain a small set of role.
    """

    pk: int
    role: str


class FunctionCall(TypedDict):
    """Function name and args in tool call.

    `arguments` is a json encoded string
    """

    name: str
    arguments: str


class ToolCall(TypedDict):
    """Tool call."""

    id: str
    type: Literal["function"]
    function: FunctionCall


class Message(BaseEntity):
    """**table_name**: `messages`.

    Message between user and agent.

    This table contain the text part of the message for quick access.
    Other part like tool-call, document, pdf, image, ... is saved in MessagePart
    Tool response is saved here in the `content_text` column
    Other stuff like annotation will be save somewhere else
    """

    pk: int
    id: UUID
    conversation_pk: int
    ai_model_pk: int
    created_at: datetime
    deleted_at: datetime | None
    role_pk: int  # Foreign key to MessageRole table
    content_text: str
    tool_call: ToolCall | None


class MessagePart(BaseEntity):
    """**table_name**: `message_parts`.

    Message parts, can contain text, tool_call, media.
    """

    pk: int
    message_pk: int
    index: int
    type: str
    content: str


class MessageCitationReferenceType(BaseEntity):
    """**table_name**: `message_citation_types`.

    Only modify on new DB version.

    Reference type.
    """

    pk: int
    reference_type: str


class MessageCitation(BaseEntity):
    """**table_name**: `message_citations`.

    `reference_type` is foreign key to MessageCitationReferenceType
    """

    pk: int
    message_pk: int
    start_index: int
    end_index: int
    reference_type_pk: int
    title: str
    src: str
    content: str
