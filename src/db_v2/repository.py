"""Repository base class."""

from src.db_v2.base import BaseEntity

from abc import ABC
from typing import Sequence

from sqlalchemy import (
    Select,
    select,
)
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.ext.asyncio import AsyncSession


class Repository[TEntity: BaseEntity, TKey](ABC):
    """Base repository class."""

    model: type[BaseEntity]
    key: InstrumentedAttribute

    async def getById(self, session: AsyncSession, key: TKey) -> TEntity | None:
        """Get entity by its primary key."""
        return await self.selectOne(
            session,
            select(self.model).where(self.key == key).limit(1),  # noqa
        )

    @staticmethod
    async def selectOne(session: AsyncSession, stmt: Select) -> TEntity | None:
        """Execute select statement and return single entity or None."""
        res = await session.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def selectMany(
        session: AsyncSession,
        stmt: Select,
    ) -> Sequence[TEntity]:
        """Execute select statement and return multiple entities."""
        res = await session.execute(stmt)
        return res.scalars().all()
