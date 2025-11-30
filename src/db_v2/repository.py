"""Repository base class."""

from src.db_v2.base import BaseEntity

from abc import ABC
from typing import Sequence

from sqlalchemy import (
    Select,
    select,
)
from sqlalchemy.orm import InstrumentedAttribute, load_only, selectinload
from sqlalchemy.ext.asyncio import AsyncSession


type ColumnList = Sequence[InstrumentedAttribute] | None
type RelationLoadMap = dict[InstrumentedAttribute, ColumnList] | None


class Repository[TEntity: BaseEntity, TKey](ABC):
    """Base repository class."""

    def __init__(self, model: type[TEntity], key: InstrumentedAttribute[TKey]):
        """Initialize repository with model and primary key attribute."""
        self.model = model
        self.key = key

    async def getByKey(
        self,
        session: AsyncSession,
        key: TKey,
        load_columns: ColumnList = None,
        load_relations: RelationLoadMap = None,
    ) -> TEntity | None:
        """Get entity by its primary key."""
        stmt = select(self.model).where(self.key.__eq__(key)).limit(1)
        stmt = self.buildOptions(
            stmt,
            load_columns,
            load_relations,
        )
        return await self.selectOne(
            session,
            stmt,
        )

    async def getManyByKeys(
        self,
        session: AsyncSession,
        keys: Sequence[TKey],
        load_columns: ColumnList = None,
        load_relations: RelationLoadMap = None,
    ) -> Sequence[TEntity]:
        """Get multiple entities by their primary keys."""
        stmt = select(self.model).where(self.key.in_(keys))
        stmt = self.buildOptions(
            stmt,
            load_columns,
            load_relations,
        )
        return await self.selectMany(session, stmt)

    async def getAll(
        self,
        session: AsyncSession,
        load_columns: ColumnList = None,
        load_relations: RelationLoadMap = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Sequence[TEntity]:
        """Get all entities of this type."""
        stmt = select(self.model)
        stmt = self.buildOptions(
            stmt,
            load_columns,
            load_relations,
        )
        if offset is not None:
            stmt.offset(offset)
        if limit is not None:
            stmt.limit(limit)
        return await self.selectMany(
            session,
            stmt,
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
        entity = await self.getByKey(session, key, [self.key])
        if entity:
            await session.delete(entity)

    async def deleteManyByKeys(
        self, session: AsyncSession, keys: Sequence[TKey]
    ) -> None:
        """Delete multiple entities by their primary keys."""
        entities = await self.getManyByKeys(session, keys, [self.key])
        for entity in entities:
            await session.delete(entity)

    @staticmethod
    async def selectOne(session: AsyncSession, stmt: Select) -> TEntity | None:
        """Execute select statement and return single entity or None."""
        res = await session.execute(stmt)
        return res.scalars().first()

    @staticmethod
    def buildOptions(
        select_stmt: Select,
        load_columns: ColumnList = None,
        load_relations: RelationLoadMap = None,
    ):
        """Build SQLAlchemy options for loading columns and relations."""
        if load_columns:
            select_stmt = select_stmt.options(
                *[load_only(col) for col in load_columns]
            )
        if load_relations:
            select_stmt = select_stmt.options(
                *[
                    selectinload(rel).load_only(*cols)
                    if cols
                    else selectinload(rel)
                    for rel, cols in load_relations.items()
                ]
            )
        return select_stmt

    @staticmethod
    async def selectMany(
        session: AsyncSession,
        stmt: Select,
    ) -> Sequence[TEntity]:
        """Execute select statement and return multiple entities."""
        res = await session.execute(stmt)
        return res.scalars().all()
