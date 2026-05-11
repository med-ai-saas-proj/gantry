from gantry.db import Repository

from .types import ConversationMetadata
from .models import Message, Conversation

import uuid
from math import e
from typing import Literal, Sequence

from sqlalchemy import func, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession


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

    async def getMessageByUuid(
        self,
        session: AsyncSession,
        conversation_uuid: uuid.UUID,
        project_id: int,
        message_uid: uuid.UUID,
    ) -> Message | None:
        stmt = (
            select(Message)
            .select_from(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                Conversation.uuid == conversation_uuid,
                Conversation.project_id == project_id,
                Message.uuid == message_uid,
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def getMessagesByUuids(
        self,
        session: AsyncSession,
        conversation_uuid: uuid.UUID,
        project_id: int,
        message_uids: Sequence[uuid.UUID],
    ) -> Sequence[Message]:
        stmt = (
            select(Message)
            .select_from(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                Conversation.uuid == conversation_uuid,
                Conversation.project_id == project_id,
                Message.uuid.in_(message_uids),
            )
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    async def getMessagesByConversationId(
        self,
        session: AsyncSession,
        conversation_id: int,
        limit: int = 20,
        last_cursor: uuid.UUID | None = None,
        order_by: Literal["asc", "desc"] = "asc",
    ) -> Sequence[Message]:
        stmt = (
            select(Message)
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )

        if last_cursor is not None:
            uuid_to_id_subquery = (
                select(Message.id)
                .select_from(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.uuid == last_cursor,
                )
            ).scalar_subquery()
            if order_by == "asc":
                effective_id = func.coalesce(uuid_to_id_subquery, 0)
                stmt = stmt.where(Message.id > effective_id)
                stmt = stmt.order_by(Message.id.asc())
            else:
                effective_id = func.coalesce(
                    uuid_to_id_subquery, func.pow(2, 63) - 1
                )
                stmt = stmt.where(Message.id < effective_id)
                stmt = stmt.order_by(Message.id.desc())
        else:
            if order_by == "asc":
                stmt = stmt.order_by(Message.id.asc())
            else:
                stmt = stmt.order_by(Message.id.desc())

        stmt = stmt.limit(limit)
        res = await session.execute(stmt)
        return res.scalars().all()

    async def deleteMessageByUuid(
        self,
        session: AsyncSession,
        conversation_uuid: uuid.UUID,
        project_id: int,
        message_uid: uuid.UUID,
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
                Message.uuid == message_uid,
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
            )
            .values(extra_metadata=extra_metadata)
            .returning(Conversation)
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
