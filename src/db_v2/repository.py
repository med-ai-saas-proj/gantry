"""Repository base class."""

from src.db_v2.base import BaseEntity

from abc import ABC
from typing import Sequence

from sqlalchemy import (
    Select,
    select,
)
from sqlalchemy.orm import InstrumentedAttribute, selectinload
from sqlalchemy.ext.asyncio import AsyncSession


class Repository[TEntity: BaseEntity, TKey](ABC):
    """Base repository class."""

    def __init__(self, model: type[TEntity], key: InstrumentedAttribute[TKey]):
        """Initialize repository with model and primary key attribute."""
        self.model = model
        self.key = key

    async def getByKey(
        self, session: AsyncSession, key: TKey
    ) -> TEntity | None:
        """Get entity by its primary key."""
        return await self.selectOne(
            session,
            select(self.model).where(self.key == key).limit(1),  # noqa
        )

    async def getManyByKeys(
        self, session: AsyncSession, keys: Sequence[TKey]
    ) -> Sequence[TEntity]:
        """Get multiple entities by their primary keys."""
        return await self.selectMany(
            session,
            select(self.model).where(self.key.in_(keys)),
        )

    async def getAll(self, session: AsyncSession) -> Sequence[TEntity]:
        """Get all entities of this type."""
        return await self.selectMany(
            session,
            select(self.model),
        )

    async def add(self, session: AsyncSession, entity: TEntity) -> None:
        """Add a new entity to the session."""
        session.add(entity)
        await session.flush()

    async def addMany(
        self, session: AsyncSession, entities: Sequence[TEntity]
    ) -> None:
        """Add multiple entities to the session."""
        session.add_all(entities)

    async def delete(self, session: AsyncSession, entity: TEntity) -> None:
        """Delete an entity from the session."""
        await session.delete(entity)

    async def deleteByKey(self, session: AsyncSession, key: TKey) -> None:
        """Delete an entity by its primary key."""
        entity = await self.getByKey(session, key)
        if entity:
            await session.delete(entity)

    async def deleteManyByKeys(
        self, session: AsyncSession, keys: Sequence[TKey]
    ) -> None:
        """Delete multiple entities by their primary keys."""
        entities = await self.getManyByKeys(session, keys)
        for entity in entities:
            await session.delete(entity)

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
