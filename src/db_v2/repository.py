from abc import abstractmethod, ABC
from dataclasses import asdict
from typing import Generic, TypeVar, Callable, get_type_hints
from typing import Any, Optional
from sqlalchemy.sql import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import Table, Column, delete, insert, select, Select, RowMapping

from src.db_v2.base import BaseEntity, TableColumns

TKey = TypeVar('TKey')
TEntity = TypeVar('TEntity', bound=BaseEntity)


class OperationBuilder(Generic[TEntity]):
    def __init__(self, session: AsyncSession, stmt, repo: "Repository", mapping_many: bool = False):
        self.session = session
        self.stmt = stmt
        self.repo = repo
        self._returning_columns: Optional[list[ColumnElement[Any]]] = None
        self.many = mapping_many

    def returning(self, *columns: ColumnElement[Any]):
        """Mark query as RETURNING specific columns or all if none passed."""
        if columns:
            self._returning_columns = list(columns)
        else:
            self._returning_columns = self.repo.columns
        return self

    async def _run(self) -> None | TEntity | list[TEntity] | tuple | list[tuple]:
        """Internal async executor called when awaited."""
        if self._returning_columns:
            res = await self.session.execute(self.stmt.returning(*self._returning_columns))
            if self.many:
                rows = res.mappings().all()
                result = [self.repo.to_entity(row) for row in rows]
            else:
                row = res.mappings().first()
                result = self.repo.to_entity(row) if row else None
        else:
            await self.session.execute(self.stmt)
            result = None
        return result

    def __await__(self):
        return self._run().__await__()

class Repository(ABC, Generic[TEntity, TKey]):
    @property
    @abstractmethod
    def table(self) -> Table:
        """SQLAlchemy Table must be defined in subclass"""
        raise NotImplementedError

    @property
    @abstractmethod
    def c(self) -> type[TableColumns]:
        """TableColumns must be defined in subclass"""
        raise NotImplementedError

    @property
    @abstractmethod
    def entity_type(self) -> type[TEntity]:
        """Entity type must be defined in subclass"""
        raise NotImplementedError

    def __init__(self):
        self.columns: list[Column] = []
        type_hints = get_type_hints(self.c)
        for attr_name, attr_type in type_hints.items():
            column = getattr(self.c, attr_name, None)
            if isinstance(column, Column):
                self.columns.append(column)
        print(f"Initialized Repo for table {self.table.name} with columns: {[col.name for col in self.columns]}")

    def to_entity(self, data: RowMapping) -> TEntity:
        return self.entity_type(**data)

    def to_dict(self, entity: TEntity) -> dict[str, Any]:
        data = asdict(entity)
        data.pop("created_at", None)
        data.pop("updated_at", None)
        if self.entity_type.__key__ in data and data[self.entity_type.__key__] is None:
            data.pop(self.entity_type.__key__)
        return data

    @staticmethod
    async def select_one(session: AsyncSession,
                         stmt: Select,
                         mapping: Callable[[RowMapping], any]) -> any:
        res = await session.execute(stmt)
        row = res.mappings().first()
        if row:
            return mapping(row)
        return None

    @staticmethod
    async def select_many(session: AsyncSession,
                          stmt: Select,
                          mapping: Callable[[RowMapping], any]) -> list[TEntity]:
        res = await session.execute(stmt)
        rows = res.mappings().all()
        return [mapping(row) for row in rows]

    async def get_one(self, session: AsyncSession, stmt: Select) -> TEntity | None:
        return await self.select_one(
            session,
            stmt,
            self.to_entity
        )

    async def get_many(self, session: AsyncSession, stmt: Select) -> list[TEntity]:
        return await self.select_many(
            session,
            stmt,
            self.to_entity
        )

    async def get_all(self, session: AsyncSession) -> list[TEntity]:
        return await self.select_many(
            session,
            select(self.table),
            self.to_entity
        )

    async def get_by_id(self, session: AsyncSession, record_id: TKey) -> TEntity | None:
        key_column: Column[TKey] = getattr(self.c, self.c.__key__)
        if key_column is None:
            raise ValueError("TableColumns must define a KEY column for update")

        return await self.select_one(
            session,
            select(self.table).where(key_column == record_id).limit(1),
            self.to_entity
        )

    def insert(self,
                     session: AsyncSession,
                     record: TEntity) -> OperationBuilder[TEntity]:
        data = self.to_dict(record)
        return OperationBuilder(
            session,
            stmt=insert(self.table).values(data),
            repo=self
        )

    def insert_many(self,
                          session: AsyncSession,
                          records: list[TEntity]) -> OperationBuilder[TEntity]:
        data_list = [self.to_dict(record) for record in records]
        return OperationBuilder(
            session,
            stmt=insert(self.table).values(data_list),
            repo=self,
            mapping_many=True
        )

    def delete(self, session: AsyncSession, record_id: TKey) -> OperationBuilder[TEntity]:
        key_column: Column[TKey] = getattr(self.c, self.c.__key__)
        if key_column is None:
            raise ValueError("TableColumns must define a KEY column for update")
        return OperationBuilder(
            session,
            stmt=(
                delete(self.table)
                .where(key_column == record_id)
            ),
            repo=self
        )

    def delete_many(self, session: AsyncSession,
                          record_ids: list[TKey]) -> OperationBuilder[TEntity]:
        key_column: Column[TKey] = getattr(self.c, self.c.__key__)
        if key_column is None:
            raise ValueError("TableColumns must define a KEY column for update")

        return OperationBuilder(
            session,
            stmt=(
                delete(self.table)
                .where(key_column.in_(record_ids))
            ),
            repo=self,
            mapping_many=True
        )

    def update(self, session: AsyncSession, record: TEntity) -> OperationBuilder[TEntity]:
        data = self.to_dict(record)
        key = self.entity_type.__key__

        if not data.get(key):
            raise ValueError("Record must have an KEY value for update")
        record_id = data.pop(key)

        key_column: Column[TKey] = getattr(self.c, self.c.__key__)
        if key_column is None:
            raise ValueError("TableColumns must define a KEY column for update")

        return OperationBuilder(
            session,
            stmt=(
                self.table.update()
                .where(key_column == record_id)
                .values(data)
            ),
            repo=self
        )
