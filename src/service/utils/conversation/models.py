from src.db.base import BaseSQLModel
from src.db.utils import (
    WithID,
    WithClientUUID,
    WithCreateUpdateTimestamp,
)
from src.service.utils.conversation.types import MessagePart

from sqlalchemy import Text, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB


class ConversationBaseSQLModel(BaseSQLModel):
    """Base SQL Model for this module only."""

    __abstract__ = True
    __table_args__ = {"schema": "Conversation"}


class Conversation(
    WithCreateUpdateTimestamp, WithID, WithClientUUID, ConversationBaseSQLModel
):
    """Represents a conversation in the agent system."""

    __tablename__ = "Conversations"
    title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    project_id: Mapped[int] = mapped_column(nullable=False, index=True)


#
# class MessagePart(TypedDict):
#     """Represents a part of a message in a conversation."""
#
#     part_kind: str
#     timestamp: Optional[str]
#     content: Any
#     tool_name: Optional[str]
#     tool_call_id: Optional[str]
#     metadata: Any | None
#
#     provider_details: Any | None
#     id: str | None
#
#     provider_name: str | None
#     signature: str | None
#
#     args: Any


class Message(WithCreateUpdateTimestamp, WithID, ConversationBaseSQLModel):
    """Represents a message in a conversation."""

    __tablename__ = "Messages"
    conversation_id: Mapped[int] = mapped_column(nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=True)
    parts: Mapped[list[MessagePart]] = mapped_column(JSONB, nullable=False)

    # metadata fields
    model_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timestamp: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
