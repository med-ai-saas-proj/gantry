from src.db.base import BaseSQLModel
from src.db.utils import (
    WithID,
    WithUUID,
    WithClientUUID,
    WithCreateUpdateTimestamp,
)
from src.management.project.models import Project
from src.service.utils.conversation.types import MessagePart

from typing import TypedDict
from datetime import datetime

from sqlalchemy import String, ForeignKey, FetchedValue
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import DateTime, BigInteger
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
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Project.id, ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    extra_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


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


class Message(WithID, WithUUID, ConversationBaseSQLModel):
    """Represents a message in a conversation."""

    __tablename__ = "Messages"
    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Conversation.id, ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    seq_id: Mapped[int] = mapped_column(
        BigInteger,
        index=True,
        nullable=False,
        init=False,
        server_default=FetchedValue(),
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=True)
    parts: Mapped[list[MessagePart]] = mapped_column(JSONB, nullable=False)

    # metadata fields
    model_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    @classmethod
    def parse_raw(cls, raw: dict) -> "Message":
        mess = Message(
            conversation_id=raw["conversation_id"],
            kind=raw["kind"],
            parts=raw["parts"],
            model_name=raw.get("model_name"),
            timestamp=raw["timestamp"],
            run_id=raw.get("run_id"),
        )
        mess.id = raw["id"]
        mess.uuid = raw["uuid"]
        mess.seq_id = raw["seq_id"]
        return mess
