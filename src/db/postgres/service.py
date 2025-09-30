from src.shared.consts import messages_const
from src.shared.utils.logger import LOGGER
from src.shared.entities.base import BaseEntity
from src.shared.custom_types.base import BaseDict
from src.db.postgres.query_builder import (
    SqlText,
    ConditionItem,
    BaseSqlQueryBuilder,
    SqlConditionInterface,
    literal_object,
    literal_objects,
)
from src.shared.custom_types.responses import CErrorResponse

from .repository import PostgresRepo

from typing import (
    Union,
    Literal,
    TypeVar,
    overload,
)
from contextlib import _GeneratorContextManager
from collections.abc import Callable

import numpy as np
import pandas as pd
import psycopg2.extras
from sqlalchemy.orm import Session


T = TypeVar("T", bound=BaseEntity)


class PostgresService:
    def __init__(
        self, session_scope: Callable[..., _GeneratorContextManager[Session]]
    ):
        self.session_scope = session_scope

    async def execute_raw_query(
        self, sql: str, params: Union[tuple, list] = ()
    ):
        with self.session_scope() as session:
            LOGGER.debug(f"[SQL]: {sql}")
            return (
                session.connection().exec_driver_sql(sql, tuple(params)).cursor
            )

    async def executemany_raw_query(
        self, sql: str, params: Union[tuple, list] | None = None
    ):
        with self.session_scope() as session:
            LOGGER.debug(f"[SQL]: {sql}")
            cursor = session.connection().connection.cursor()
            psycopg2.extras.execute_batch(cursor, sql, tuple(params or ()))
            return cursor

    async def get_all(self, repo: type[PostgresRepo[T]]) -> list[T]:
        query = repo.get_all()
        return repo.row_factory(
            await self.execute_raw_query(sql=query.sql, params=query.params)
        )

    async def get_by_id(self, repo: type[PostgresRepo[T]], _id) -> T | None:
        query = repo.get_by_id(_id)
        records = repo.row_factory(
            await self.execute_raw_query(sql=query.sql, params=query.params)
        )
        if len(records) == 0:
            return None
        return records[0]

    async def get_exist_by_id(self, repo: type[PostgresRepo[T]], _id) -> T:
        record = await self.get_by_id(repo, _id)
        if record is None:
            raise CErrorResponse(
                status_code=404, message=messages_const.NOT_FOUND
            )
        return record

    async def get_by_condition(
        self, repo: type[PostgresRepo[T]], conditions: SqlConditionInterface
    ) -> list[T]:
        query = repo.get_by_condition(conditions=conditions)
        return repo.row_factory(
            await self.execute_raw_query(query.sql, query.params)
        )

    @overload
    async def insert(
        self,
        repo: type[PostgresRepo[T]],
        record: T | BaseDict,
        returning: Literal[True],
    ) -> T: ...

    @overload
    async def insert(
        self,
        repo: type[PostgresRepo[T]],
        record: T | BaseDict,
        returning: Literal[False],
    ) -> None: ...

    @overload
    async def insert(
        self, repo: type[PostgresRepo[T]], record: T | BaseDict
    ) -> None: ...

    async def insert(
        self,
        repo: type[PostgresRepo[T]],
        record: T | BaseDict,
        returning: bool = False,
    ) -> T | None:
        query = repo.insert(record=record, returning=returning)
        cursor = await self.execute_raw_query(
            sql=query.sql, params=query.params
        )
        if returning:
            return repo.row_factory(cursor)[0]
        return None

    @overload
    async def insert_on_conflict_do_nothing(
        self,
        repo: type[PostgresRepo[T]],
        record: T | BaseDict,
        identity_columns: list[str],
        returning: Literal[True],
    ) -> T: ...

    @overload
    async def insert_on_conflict_do_nothing(
        self,
        repo: type[PostgresRepo[T]],
        record: T | BaseDict,
        identity_columns: list[str],
        returning: Literal[False],
    ) -> None: ...

    @overload
    async def insert_on_conflict_do_nothing(
        self,
        repo: type[PostgresRepo[T]],
        record: T | BaseDict,
        identity_columns: list[str],
    ) -> None: ...

    async def insert_on_conflict_do_nothing(
        self,
        repo: type[PostgresRepo[T]],
        record: T | BaseDict,
        identity_columns: list[str],
        returning: bool = False,
    ) -> T | None:
        query = repo.insert_on_conflict_do_nothing(
            record=record,
            identity_columns=identity_columns,
            returning=returning,
        )
        cursor = await self.execute_raw_query(
            sql=query.sql, params=query.params
        )
        if returning:
            return repo.row_factory(cursor)[0]
        return None

    @overload
    async def insert_many(
        self,
        repo: type[PostgresRepo[T]],
        records: list[T | BaseDict],
        returning: Literal[True],
    ) -> list[T]: ...

    @overload
    async def insert_many(
        self,
        repo: type[PostgresRepo[T]],
        records: list[T | BaseDict],
        returning: Literal[False],
    ) -> None: ...

    @overload
    async def insert_many(
        self,
        repo: type[PostgresRepo[T]],
        records: list[T | BaseDict],
        returning: bool = False,
    ) -> list[T] | None: ...

    async def insert_many(
        self,
        repo: type[PostgresRepo[T]],
        records: list[T | BaseDict],
        returning: bool = False,
    ) -> list[T] | None:
        query = repo.insert_many(records=records, returning=returning)
        cursor = await self.execute_raw_query(
            sql=query.sql, params=query.params
        )
        if returning:
            return repo.row_factory(cursor)
        return None

    @overload
    async def update(
        self,
        repo: type[PostgresRepo[T]],
        record: T | BaseDict,
        identity_columns: list[str],
        returning: Literal[True],
        text_clauses: dict[str, SqlText] | None = None,
    ) -> T: ...

    @overload
    async def update(
        self,
        repo: type[PostgresRepo[T]],
        record: T | BaseDict,
        identity_columns: list[str],
        returning: Literal[False],
        text_clauses: dict[str, SqlText] | None = None,
    ) -> None: ...

    async def update(
        self,
        repo: type[PostgresRepo[T]],
        record: T | BaseDict,
        identity_columns: list[str],
        returning: bool = False,
        text_clauses: dict[str, SqlText] | None = None,
    ) -> T | None:
        query = repo.update(
            record=record,
            identity_columns=identity_columns,
            returning=returning,
            text_clauses=text_clauses or {},
        )
        cursor = await self.execute_raw_query(
            sql=query.sql, params=query.params
        )
        if returning:
            return repo.row_factory(cursor)[0]
        return None

    @overload
    async def update_many(
        self,
        repo: type[PostgresRepo[T]],
        records: list[T],
        identity_columns: list[str],
        returning: Literal[True],
        text_clauses: dict[str, SqlText] | None = None,
    ) -> list[T]: ...

    @overload
    async def update_many(
        self,
        repo: type[PostgresRepo[T]],
        records: list[T] | list[BaseDict],
        identity_columns: list[str],
        returning: Literal[False],
        text_clauses: dict[str, SqlText] | None = None,
    ) -> None: ...

    async def update_many(
        self,
        repo: type[PostgresRepo[T]],
        records: list[T] | list[BaseDict],
        identity_columns: list[str],
        returning: bool = False,
        text_clauses: dict[str, SqlText] | None = None,
    ) -> list[T] | None:
        query = repo.update_many(
            records=records,
            identity_columns=identity_columns,
            returning=returning,
            text_clauses=text_clauses or {},
        )
        cursor = await self.execute_raw_query(
            sql=query.sql, params=query.params
        )
        if returning:
            updated_records = repo.row_factory(cursor)
            return updated_records
        return None

    @overload
    async def delete_by_condition(
        self,
        repo: type[PostgresRepo[T]],
        conditions: SqlConditionInterface,
        returning: Literal[True],
    ) -> list[T]: ...

    @overload
    async def delete_by_condition(
        self,
        repo: type[PostgresRepo[T]],
        conditions: SqlConditionInterface,
        returning: Literal[False],
    ) -> None: ...

    @overload
    async def delete_by_condition(
        self,
        repo: type[PostgresRepo[T]],
        conditions: SqlConditionInterface,
        returning: bool = False,
    ) -> list[T] | None: ...

    async def delete_by_condition(
        self,
        repo: type[PostgresRepo[T]],
        conditions: SqlConditionInterface,
        returning: bool = False,
    ) -> list[T] | None:
        query = repo.delete_by_condition(
            conditions=conditions, returning=returning
        )
        cursor = await self.execute_raw_query(
            sql=query.sql, params=query.params
        )
        if returning:
            return repo.row_factory(cursor)
        return None

    async def fast_insert_into_temp(
        self,
        target_query_builder: BaseSqlQueryBuilder,
        records: list[T] | list[BaseDict] | pd.DataFrame,
        temp_table: str,
        text_clauses: dict[str, SqlText] | None = None,
    ):
        if "#" not in temp_table:
            raise Exception(f"{temp_table} temp table not contain #")
        records = pd.DataFrame(records).replace({np.nan: None})
        chunk_size = 1
        query_values = target_query_builder.values(
            records=records.iloc[:chunk_size],
            text_clauses=text_clauses,
            execute_batch=True,
        )
        if len(records) == 0:
            return query_values
        sql_columns = ", ".join(literal_objects(query_values.columns))
        params = records.values.tolist()
        with self.session_scope():
            await self.execute_raw_query(
                "CREATE TEMPORARY TABLE IF NOT EXISTS %s OF %s;"
                % (literal_object(temp_table), target_query_builder.table_type)
            )
            sql = "INSERT INTO %s (%s) VALUES %s" % (
                literal_object(temp_table),
                sql_columns,
                query_values.sql,
            )
            for i in range(0, len(params), 10000):
                await self.executemany_raw_query(
                    sql, tuple(params[i : i + 10000])
                )
        return query_values

    def _validate_non_nested_condition(
        self, identity_columns: SqlConditionInterface
    ):
        for condition in identity_columns["conditions"]:
            if "conditions" in condition:
                raise Exception("condition is not valid")

    async def fast_upsert_from_source_table(
        self,
        target_query_builder: BaseSqlQueryBuilder,
        source_query_builder: BaseSqlQueryBuilder,
        join_conditions: SqlConditionInterface[ConditionItem],
        insert_conditions: SqlConditionInterface[ConditionItem],
        upsert_columns: list[str],
        is_update=True,
        is_insert=True,
    ):
        self._validate_non_nested_condition(insert_conditions)
        self._validate_non_nested_condition(join_conditions)
        source_alias = source_query_builder.table
        target_alias = target_query_builder.table
        query_join_conditions = BaseSqlQueryBuilder.where(
            conditions=join_conditions
        )
        # sql update
        sql_set_columns = ", ".join(
            BaseSqlQueryBuilder.set_values(
                left_sequences=literal_objects(list_text=upsert_columns),
                right_sequences=literal_objects(
                    list_text=upsert_columns, alias=source_alias
                ),
            )
        )
        sql_update = f"""
            UPDATE {target_query_builder.full_table_name} AS {literal_object(target_alias)}
            SET {sql_set_columns}
            FROM {source_query_builder.full_table_name} AS {literal_object(source_alias)}
            {query_join_conditions.add_where_operator()}
        """
        # sql insert
        sql_select_columns = ", ".join(
            literal_objects(list_text=upsert_columns, alias=source_alias)
        )
        sql_insert_columns = ", ".join(
            literal_objects(list_text=upsert_columns)
        )
        query_insert_conditions = BaseSqlQueryBuilder.where(insert_conditions)
        sql_insert_conditions = f"""
                LEFT JOIN {target_query_builder.full_table_name} {literal_object(target_alias)}
                    ON {query_join_conditions.sql}
                {query_insert_conditions.add_where_operator()}
            """
        sql_insert = f"""
            --SET NOCOUNT ON;
            INSERT INTO {target_query_builder.full_table_name} ({sql_insert_columns})
            SELECT {sql_select_columns}
            FROM {literal_object(source_alias)}
            {sql_insert_conditions}
        """
        list_sql = (
            [sql_update]
            if is_update and len(join_conditions["conditions"]) != 0
            else []
        )
        if is_insert:
            list_sql += [sql_insert]
        sql = ";\n".join(list_sql)
        with self.session_scope():
            await self.execute_raw_query(
                sql,
                params=query_join_conditions.params
                + query_insert_conditions.params,
            )
        return

    async def fast_insert_on_conflict_do_nothing(
        self,
        target_query_builder: BaseSqlQueryBuilder,
        temp_table: str,
        records: list[T] | list[BaseDict] | pd.DataFrame,
        join_conditions: SqlConditionInterface[ConditionItem],
        insert_conditions: SqlConditionInterface[ConditionItem],
        text_clauses: dict[str, SqlText] | None = None,
    ):
        self._validate_non_nested_condition(join_conditions)
        self._validate_non_nested_condition(insert_conditions)
        with self.session_scope():
            # temp_table = f"#{cls.query_builder.table}"
            if len(records) > 0:
                query = await self.fast_insert_into_temp(
                    target_query_builder=target_query_builder,
                    records=records,
                    temp_table=temp_table,
                    text_clauses=text_clauses,
                )
                await self.fast_upsert_from_source_table(
                    target_query_builder=target_query_builder,
                    source_query_builder=BaseSqlQueryBuilder(
                        table=temp_table, schema=None
                    ),
                    join_conditions=join_conditions,
                    insert_conditions=insert_conditions,
                    upsert_columns=query.columns,
                    is_update=False,
                )
                await self.execute_raw_query(f'DROP TABLE "{temp_table}"')
        return

    async def fast_upsert(
        self,
        target_query_builder: BaseSqlQueryBuilder,
        temp_table: str,
        records: list[T] | list[BaseDict] | pd.DataFrame,
        join_conditions: SqlConditionInterface[ConditionItem],
        insert_conditions: SqlConditionInterface[ConditionItem],
        text_clauses: dict[str, SqlText] | None = None,
        is_update=True,
        is_insert=True,
    ):
        with self.session_scope():
            # temp_table = f"#{cls.query_builder.table}"
            if len(records) > 0:
                query = await self.fast_insert_into_temp(
                    target_query_builder=target_query_builder,
                    records=records,
                    temp_table=temp_table,
                    text_clauses=text_clauses,
                )
                await self.fast_upsert_from_source_table(
                    target_query_builder=target_query_builder,
                    source_query_builder=BaseSqlQueryBuilder(
                        table=temp_table, schema=None
                    ),
                    join_conditions=join_conditions,
                    insert_conditions=insert_conditions,
                    upsert_columns=query.columns,
                    is_insert=is_insert,
                    is_update=is_update,
                )
                await self.execute_raw_query(f'DROP TABLE "{temp_table}"')
        return

    async def lock_table(
        self, repo: type[PostgresRepo[T]], mode="ACCESS EXCLUSIVE"
    ):
        with self.session_scope():
            query = repo.lock_table(mode)
            await self.execute_raw_query(sql=query.sql, params=query.params)
        return

    async def get_order_columns(
        self, repo: type[PostgresRepo[T]], exclude_columns: list[str] = []
    ) -> list[str]:
        conditions: SqlConditionInterface = {
            "logical": "and",
            "conditions": [
                {
                    "field": "table_schema",
                    "operator": "=",
                    "value": repo.query_builder.schema,
                },
                {
                    "field": "table_name",
                    "operator": "=",
                    "value": repo.query_builder.table,
                },
            ],
        }
        if exclude_columns is not None and len(exclude_columns) > 0:
            conditions: SqlConditionInterface = {
                "logical": "and",
                "conditions": [
                    {
                        "field": "column_name",
                        "operator": "NOT IN",
                        "value": exclude_columns,
                    },
                    conditions,
                ],
            }
        condition_query = repo.query_builder.where(conditions)
        sql = f"""
            SELECT *
            FROM information_schema.columns
            {condition_query.add_where_operator()}
            ORDER BY column_name ASC
        """
        cur = await self.execute_raw_query(
            sql=sql, params=condition_query.params
        )
        return [row["column_name"] for row in repo.row_factory(cur=cur)]  # type: ignore

    # async def get_for_update(
    #     self, conditions: SqlConditionInterface, session: Session, mode="FOR UPDATE", no_wait=False
    # ):
    #     query = await cls.query_builder.where(conditions=conditions)
    #     sql = f"SELECT * FROM {cls.query_builder.full_table_name} WHERE {query.sql} {mode}"
    #     if no_wait:
    #         sql += " NOWAIT"
    #     session.connection().exec_driver_sql(sql, tuple(query.params))
    #     return
