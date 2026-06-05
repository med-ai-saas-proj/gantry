from .models import ConversationType

import uuid
from typing import Sequence
from datetime import datetime

from pydantic import BaseModel
from ag_ui.core.types import Message as AgUiMessage


class Message(BaseModel):
    message_uid: uuid.UUID
    payload: AgUiMessage | dict
    run_id: str | None
    timestamp: datetime
    extra_metadata: dict | None = None


class AddMessageRequest(BaseModel):
    """Represents a request to add a message to a conversation."""

    messages: Sequence[Message]


class AddTreeMessageRequest(AddMessageRequest):
    from_message_uid: uuid.UUID | None = None


class GetMessagesByUuidsRequest(BaseModel):
    """Represents a request to retrieve multiple messages by UID."""

    message_uids: Sequence[uuid.UUID]


class CreateConversationRequest(BaseModel):
    """Represents a request to create a new conversation."""

    extra_metadata: dict | None = None
    messages: Sequence[Message] | None = None


class CreateConversationResponse(BaseModel):
    """Represents a response after creating a new conversation."""

    conversation_uid: uuid.UUID


class ConversationMetadataResponse(BaseModel):
    """Represents the metadata of a conversation."""

    conversation_uid: uuid.UUID
    project_id: int
    extra_metadata: dict | None = None
    created_at: datetime
    tree_structure: dict[str, str] | None
    active_leaf_message_id: uuid.UUID | None = None
    conversation_type: ConversationType
    relationships_map: dict[str, str] | None = None


class UpdateConversationMetadataRequest(BaseModel):
    """Represents a request to update a conversation."""

    extra_metadata: dict | None = None
