"""Repository base class."""

from abc import ABC
from typing import Sequence

from sqlalchemy import (
    Select,
    ColumnElement,
    UnaryExpression,
    func,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    InstrumentedAttribute,
    load_only,
    joinedload,
    selectinload,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.strategy_options import _AbstractLoad


type ColumnList = Sequence[InstrumentedAttribute] | None
type RelationLoadMap = (
    dict[InstrumentedAttribute, ColumnList | RelationLoadMap] | None
)


class Repository[TEntity: DeclarativeBase, TKey](ABC):
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
        filters: list[ColumnElement] | None = None,
        sorting: UnaryExpression | None = None,
    ) -> tuple[Sequence[TEntity], int]:
        """Get all entities of this type."""
        stmt = select(self.model, func.count().over().label("total_count"))
        stmt = self.buildOptions(
            stmt,
            load_columns,
            load_relations,
        )
        stmt = self.buildFilterPagination(
            stmt,
            filters,
            offset,
            limit,
            sorting,
        )
        res = await session.execute(stmt)
        rows = res.unique().all()

        return (
            [row[0] for row in rows],
            rows[0].total_count if rows else 0,
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
        return res.unique().scalars().first()

    @staticmethod
    def buildFilterPagination(
        stmt: Select,
        filters: list[ColumnElement] | None = None,
        offset: int | None = None,
        limit: int | None = None,
        sorting: UnaryExpression | None = None,
    ) -> Select:
        """Build SQLAlchemy statement with filters, pagination, and sorting."""
        if filters is not None:
            stmt = stmt.where(*filters)
        if sorting is not None:
            stmt = stmt.order_by(sorting)
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        return stmt

    @staticmethod
    def buildOptions(
        select_stmt: Select,
        load_columns: ColumnList = None,
        load_relations: RelationLoadMap = None,
    ) -> Select:
        """Build SQLAlchemy options for loading columns and relations."""
        if load_columns:
            select_stmt = select_stmt.options(
                *[load_only(col) for col in load_columns]
            )
        if load_relations:
            select_stmt = select_stmt.options(
                *[
                    (
                        joinedload(rel).options(
                            *Repository.recursiveBuildOptions(cols_or_map)
                        )
                        if isinstance(cols_or_map, dict)
                        else (
                            joinedload(rel).load_only(*cols_or_map)
                            if cols_or_map
                            else joinedload(rel)
                        )
                    )
                    for rel, cols_or_map in load_relations.items()
                ]
            )
        return select_stmt

    @staticmethod
    def recursiveBuildOptions(
        load_relations: RelationLoadMap,
    ) -> list[_AbstractLoad]:
        """Recursively build SQLAlchemy options for loading relations."""
        if not load_relations:
            return []

        res: list[_AbstractLoad] = []
        for rel, cols_or_map in load_relations.items():
            if isinstance(cols_or_map, dict):
                nested_opts = Repository.recursiveBuildOptions(cols_or_map)
                opt = joinedload(rel).options(*nested_opts)
                res.append(opt)
            else:
                res.append(
                    joinedload(rel).load_only(*cols_or_map)
                    if cols_or_map
                    else selectinload(rel)
                )
        return res

    @staticmethod
    async def selectMany(
        session: AsyncSession,
        stmt: Select,
    ) -> Sequence[TEntity]:
        """Execute select statement and return multiple entities."""
        res = await session.execute(stmt)
        return res.unique().scalars().all()
