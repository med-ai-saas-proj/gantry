import pandas as pd
import psycopg2.extras
from contextlib import _GeneratorContextManager
from typing import Callable, Dict, List, Literal, Tuple, Type, TypeVar, Union, overload

from sqlalchemy.orm import Session
from src.custom_types.common import BaseDict
from src.query_builders.sqlserver import SqlConditionInterface, SqlText
from src.repositories import SqlserverRepo
from src.utils.logger import LOGGER


T = TypeVar("T", bound=BaseDict)


class SqlserverService:

    def __init__(self, session_scope: Callable[..., _GeneratorContextManager[Session]]):
        self.session_scope = session_scope

    async def execute_raw_query(self, sql: str, params: Union[Tuple, List] = ()):
        with self.session_scope() as session:
            LOGGER.debug(f"[SQL]: {sql}")
            return session.connection().exec_driver_sql(sql, tuple(params)).cursor

    async def executemany_raw_query(self, sql: str, params: Union[Tuple, List] = ()):
        with self.session_scope() as session:
            LOGGER.debug(f"[SQL]: {sql}")
            cursor = session.connection().connection.cursor()
            psycopg2.extras.execute_batch(cursor, sql, tuple(params))
            return cursor

    async def get_all(self, repo: Type[SqlserverRepo[T]]) -> List[T]:
        query = repo.get_all()
        return repo.row_factory(await self.execute_raw_query(sql=query.sql, params=query.params))

    async def get_by_condition(self, repo: Type[SqlserverRepo[T]], conditions: SqlConditionInterface) -> List[T]:
        query = repo.get_by_condition(conditions=conditions)
        return repo.row_factory(await self.execute_raw_query(query.sql, query.params))

    @overload
    async def insert(
        self,
        repo: Type[SqlserverRepo[T]],
        records: List[T] | pd.DataFrame,
        returning: Literal[True],
        text_clauses: Dict[str, SqlText],
    ) -> T: ...

    @overload
    async def insert(
        self,
        repo: Type[SqlserverRepo[T]],
        records: List[T] | pd.DataFrame,
        returning: Literal[False],
        text_clauses: Dict[str, SqlText],
    ) -> None: ...

    async def insert(
        self,
        repo: Type[SqlserverRepo[T]],
        records: List[T] | pd.DataFrame,
        returning: bool,
        text_clauses: Dict[str, SqlText],
    ) -> T | None:
        query = repo.insert(records=records, returning=returning, text_clauses=text_clauses)
        cursor = await self.execute_raw_query(sql=query.sql, params=query.params)
        if returning:
            return repo.row_factory(cursor)[0]
        return None

    @overload
    async def insert_on_conflict_do_nothing(
        self,
        repo: Type[SqlserverRepo[T]],
        records: List[T] | pd.DataFrame,
        conflict_conditions: SqlConditionInterface,
        returning: Literal[True],
        text_clauses: Dict[str, SqlText],
    ) -> List[T]: ...

    @overload
    async def insert_on_conflict_do_nothing(
        self,
        repo: Type[SqlserverRepo[T]],
        records: List[T] | pd.DataFrame,
        conflict_conditions: SqlConditionInterface,
        returning: Literal[False],
        text_clauses: Dict[str, SqlText],
    ) -> None: ...

    async def insert_on_conflict_do_nothing(
        self,
        repo: Type[SqlserverRepo[T]],
        records: List[T] | pd.DataFrame,
        conflict_conditions: SqlConditionInterface,
        returning: bool,
        text_clauses: Dict[str, SqlText],
    ) -> List[T] | None:
        query = repo.insert_on_conflict_do_nothing(
            records=records, conflict_conditions=conflict_conditions, returning=returning, text_clauses=text_clauses
        )
        cursor = await self.execute_raw_query(sql=query.sql, params=query.params)
        if returning:
            return repo.row_factory(cursor)
        return None

    @overload
    async def update(
        self,
        repo: Type[SqlserverRepo[T]],
        records: List[T] | pd.DataFrame,
        update_conditions: SqlConditionInterface,
        returning: Literal[True],
        text_clauses: Dict[str, SqlText],
    ) -> List[T]: ...

    @overload
    async def update(
        self,
        repo: Type[SqlserverRepo[T]],
        records: List[T] | pd.DataFrame,
        update_conditions: SqlConditionInterface,
        returning: Literal[False],
        text_clauses: Dict[str, SqlText],
    ) -> None: ...

    async def update(
        self,
        repo: Type[SqlserverRepo[T]],
        records: List[T] | pd.DataFrame,
        update_conditions: SqlConditionInterface,
        returning: bool = False,
        text_clauses: Dict[str, SqlText] = {},
    ) -> List[T] | None:
        query = repo.update(
            records=records, update_conditions=update_conditions, returning=returning, text_clauses=text_clauses
        )
        cursor = await self.execute_raw_query(sql=query.sql, params=query.params)
        if returning:
            return repo.row_factory(cursor)
        return None
