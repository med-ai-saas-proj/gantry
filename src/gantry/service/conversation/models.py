from gantry.db.base import BaseSQLModel
from gantry.db.utils import (
    WithID,
    WithUUID,
    WithClientUUID,
    WithCreateUpdateTimestamp,
)
from gantry.management.project.models import Project

import enum
import uuid
from datetime import datetime

import sqlalchemy
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import UUID, DateTime, BigInteger
from sqlalchemy.dialects.postgresql import JSONB


class ConversationBaseSQLModel(BaseSQLModel):
    """Base SQL Model for this module only."""

    __abstract__ = True
    __table_args__ = {"schema": "Conversation"}


class ConversationType(str, enum.Enum):
    """Enum for conversation types."""

    SEQUENCE = "sequence"
    TREE = "tree"


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
    tree_structure: Mapped[dict[str, str] | None] = mapped_column(
        JSONB, nullable=True
    )
    active_leaf_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    relationships_map: Mapped[dict[str, str] | None] = mapped_column(
        JSONB, nullable=True
    )


from ag_ui.core.types import Message as AgUiMessage


class Message(WithID, WithUUID, ConversationBaseSQLModel):
    """Represents a message in a conversation."""

    __tablename__ = "Messages"
    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Conversation.id, ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    payload: Mapped[AgUiMessage | dict] = mapped_column(JSONB, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extra_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    @classmethod
    def parse_raw(cls, raw: dict) -> "Message":
        mess = Message(
            conversation_id=raw["conversation_id"],
            payload=raw["payload"],
            timestamp=raw["timestamp"],
            run_id=raw.get("run_id"),
            extra_metadata=raw.get("extra_metadata"),
        )
        mess.id = raw["id"]
        mess.uuid = raw["uuid"]
        return mess
