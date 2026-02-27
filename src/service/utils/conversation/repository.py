from src.db.repository import Repository
from src.service.utils.conversation.models import Message, Conversation

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ConversationRepository(Repository[Conversation, int]):
    def __init__(self):
        super().__init__(Conversation, Conversation.id)

    async def get_conversation_id(
        self,
        session: AsyncSession,
        conversation_uuid: uuid.UUID,
        project_id: int,
    ) -> int | None:
        stmt = select(Conversation).where(
            Conversation.uuid == conversation_uuid,
            Conversation.project_id == project_id,
        )
        res = await session.execute(stmt)
        conversation = res.scalar_one_or_none()
        return conversation.id if conversation else None

    async def get_messages_by_conversation_id(
        self, session: AsyncSession, conversation_id: int
    ) -> Sequence[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.asc())
        )
        res = await session.execute(stmt)
        return res.unique().scalars().all()
