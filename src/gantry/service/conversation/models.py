from gantry.db.base import BaseSQLModel
from gantry.db.utils import (
    WithID,
    WithUUID,
    WithClientUUID,
    WithCreateUpdateTimestamp,
)
from gantry.management.project.models import Project
from gantry.service.conversation.types import MessagePart

import enum
import uuid
from typing import TypedDict
from datetime import datetime

import sqlalchemy
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import DateTime, BigInteger
from sqlalchemy.dialects.postgresql import JSONB


class ConversationBaseSQLModel(BaseSQLModel):
    """Base SQL Model for this module only."""

    __abstract__ = True
    __table_args__ = {"schema": "Conversation"}


class ConversationType(str, enum.Enum):
    """Enum for conversation types."""

    SEQUENCE = "sequence"
    CHECKPOINT = "checkpoint"


class TreeNode(TypedDict):
    """Represents a node in the conversation tree structure."""

    message_id: uuid.UUID
    parent_id: uuid.UUID | None


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
    conversation_type: Mapped[ConversationType] = mapped_column(
        sqlalchemy.Enum(ConversationType, schema="Conversation"),
        nullable=False,
        server_default=ConversationType.SEQUENCE,
    )
    tree_structure: Mapped[list[TreeNode] | None] = mapped_column(
        JSONB, nullable=True
    )


class Message(WithID, WithUUID, ConversationBaseSQLModel):
    """Represents a message in a conversation."""

    __tablename__ = "Messages"
    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Conversation.id, ondelete="CASCADE"),
        index=True,
        nullable=False,
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
        return mess
