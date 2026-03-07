from src.db.repository import Repository
from src.service.utils.conversation.models import Message, Conversation

import uuid
from typing import Literal, Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.service.utils.conversation.types import ConversationMetadata


class ConversationRepository(Repository[Conversation, int]):
    def __init__(self):
        super().__init__(Conversation, Conversation.id)

    async def getConversationMetadataByUUID(
        self,
        session: AsyncSession,
        conversation_uuid: uuid.UUID,
        project_id: int,
    ) -> ConversationMetadata | None:
        stmt = (
            select(Conversation)
            .select_from(Conversation)
            .where(
                Conversation.uuid == conversation_uuid,
                Conversation.project_id == project_id,
            )
        )
        res = await session.execute(stmt)
        conversation = res.scalar_one_or_none()
        return (
            {
                "conversation_id": conversation.id,
                "conversation_uid": conversation.uuid,
                "project_id": conversation.project_id,
                "extra_metadata": conversation.extra_metadata,
                "created_at": conversation.created_at,
            }
            if conversation
            else None
        )

    async def getMessageBySeqId(
        self,
        session: AsyncSession,
        conversation_uuid: uuid.UUID,
        project_id: int,
        message_seq_id: int,
    ) -> Message | None:
        stmt = (
            select(Message)
            .select_from(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                Conversation.uuid == conversation_uuid,
                Conversation.project_id == project_id,
                Message.seq_id == message_seq_id,
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def getMessagesByConversationId(
        self,
        session: AsyncSession,
        conversation_id: int,
        limit: int = 20,
        last_cursor: int | None = None,
        order_by: Literal["asc", "desc"] = "asc",
    ) -> Sequence[Message]:
        stmt = (
            select(Message)
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )

        if order_by == "asc":
            if last_cursor is not None:
                stmt = stmt.where(Message.seq_id > last_cursor)
            stmt = stmt.order_by(Message.seq_id.asc())
        else:
            if last_cursor is not None:
                stmt = stmt.where(Message.seq_id < last_cursor)
            stmt = stmt.order_by(Message.seq_id.desc())

        stmt = stmt.limit(limit)
        res = await session.execute(stmt)
        return res.scalars().all()

    async def deleteMessageBySeqId(
        self,
        session: AsyncSession,
        conversation_uuid: uuid.UUID,
        project_id: int,
        message_seq_id: int,
    ) -> int | None:
        stmt = (
            delete(Message)
            .where(
                Message.conversation_id.in_(
                    select(Conversation.id)
                    .select_from(Conversation)
                    .where(
                        Conversation.uuid == conversation_uuid,
                        Conversation.project_id == project_id,
                    )
                ),
                Message.seq_id == message_seq_id,
            )
            .returning(Message.id)
        )
        res = await session.execute(stmt)
        deleted_message_id = res.scalar_one_or_none()
        return deleted_message_id

    async def deleteConversationByUUID(
        self,
        session: AsyncSession,
        conversation_uuid: uuid.UUID,
        project_id: int,
    ) -> int | None:
        stmt = (
            delete(Conversation)
            .where(
                Conversation.uuid == conversation_uuid,
                Conversation.project_id == project_id,
            )
            .returning(Conversation.id)
        )
        res = await session.execute(stmt)
        deleted_conversation_id = res.scalar_one_or_none()
        return deleted_conversation_id

    async def updateConversationMetadataByUUID(
        self,
        session: AsyncSession,
        conversation_uuid: uuid.UUID,
        project_id: int,
        extra_metadata: dict | None,
    ) -> ConversationMetadata | None:
        stmt = (
            update(Conversation)
            .where(
                Conversation.uuid == conversation_uuid,
                Conversation.project_id == project_id,
            ).values(extra_metadata=extra_metadata).returning(Conversation)
        )
        res = await session.execute(stmt)
        conversation = res.scalar_one_or_none()
        if conversation is None:
            return None
        
        return {
            "conversation_id": conversation.id,
            "conversation_uid": conversation.uuid,
            "project_id": conversation.project_id,
            "extra_metadata": conversation.extra_metadata,
            "created_at": conversation.created_at,
        }