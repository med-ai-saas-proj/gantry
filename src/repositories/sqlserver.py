import json
from typing import Dict, Generic, List, TypeVar
import pandas as pd
from src.custom_types.common import BaseDict
from src.query_builders.sqlserver import (
    PLACEHOLDER,
    SqlConditionInterface,
    SqlQuery,
    SqlText,
    SqlserverQueryBuilder,
    literal_objects,
)

T = TypeVar("T", bound=BaseDict)


class SqlserverRepo(Generic[T]):
    query_builder: SqlserverQueryBuilder
    json_columns: List[str] = []

    @classmethod
    def dump_records(cls, records: List[T]) -> List[T]:
        results = []
        for record in records:
            result = record.copy()
            for field in cls.json_columns:
                if field in result:
                    result[field] = json.dumps(result[field])
            results.append(result)
        return results

    @classmethod
    def load_records(cls, records: List[T]) -> List[T]:
        results = []
        for record in records:
            result = record.copy()
            for field in cls.json_columns:
                if field in result:
                    result[field] = json.loads(result[field])
            results.append(result)
        return results

    @classmethod
    def data_frame_factory(cls, cur) -> pd.DataFrame:
        if cur.description is None:
            return pd.DataFrame()
        columns = [column[0] for column in cur.description]
        results = [list(row) for row in cur.fetchall()]
        return pd.DataFrame(results, columns=pd.Series(columns))

    @classmethod
    def row_factory(cls, cur) -> List[T]:
        if cur.description is None:
            return []
        columns = [column[0] for column in cur.description]
        results = []
        for row in cur.fetchall():
            results.append(dict(zip(columns, row)))
        return results

    @classmethod
    def get_all(cls):
        sql = f"SELECT * FROM {PLACEHOLDER}" % cls.query_builder.full_table_name
        return SqlQuery(sql=sql)

    @classmethod
    def get_by_condition(cls, conditions: SqlConditionInterface):
        query = cls.query_builder.where(conditions=conditions)
        sql = f"SELECT * FROM {cls.query_builder.full_table_name} WHERE {query.sql}"
        return SqlQuery(sql=sql, params=query.params)

    @classmethod
    def insert(
        cls,
        records: List[T] | pd.DataFrame,
        returning: bool,
        text_clauses: Dict[str, SqlText],
    ):
        if len(records) == 0:
            raise ValueError("[ERROR][REPO]: Empty records")
        query_values = cls.query_builder.values(records, text_clauses=text_clauses)
        sql_columns = ", ".join(literal_objects(query_values.columns))
        sql_returning = "\nOUTPUT INSERTED.*" if returning else ""
        sql = "INSERT INTO %s (%s)%s\nVALUES %s" % (
            cls.query_builder.full_table_name,
            sql_columns,
            sql_returning,
            query_values.sql,
        )
        return SqlQuery(sql=sql, params=query_values.params, columns=query_values.params)

    @classmethod
    def insert_on_conflict_do_nothing(
        cls,
        records: List[T] | pd.DataFrame,
        conflict_conditions: SqlConditionInterface,
        returning: bool,
        text_clauses: Dict[str, SqlText],
    ):
        if len(records) == 0:
            raise ValueError("[ERROR][REPO]: Empty records")
        query_conflict_conditions = cls.query_builder.where(conditions=conflict_conditions)
        query_values = cls.query_builder.values(records, text_clauses=text_clauses)
        sql_columns = ", ".join(literal_objects(query_values.columns))
        sql_select_columns = ", ".join(literal_objects(query_values.columns, alias="s"))
        sql_returning = "\nOUTPUT INSERTED.*" if returning else ""
        sql = (
            f"INSERT INTO {cls.query_builder.full_table_name} ({sql_columns})"
            + sql_returning
            + f"\nSELECT {sql_select_columns} FROM (VALUES {query_values.sql}) as s({sql_columns})"
            + f"\nWHERE NOT EXISTS (SELECT 1 FROM {cls.query_builder.full_table_name} t WHERE {query_conflict_conditions.sql})"
        )
        return SqlQuery(sql=sql, params=query_values.params, columns=query_values.params)

    @classmethod
    def insert_on_conflict_do_update(
        cls,
        records: List[T] | pd.DataFrame,
        conflict_conditions: SqlConditionInterface,
        text_clauses: Dict[str, SqlText],
    ):
        if len(records) == 0:
            raise ValueError("[ERROR][REPO]: Empty records")
        query_conflict_conditions = cls.query_builder.where(conditions=conflict_conditions)
        query_values = cls.query_builder.values(records, text_clauses=text_clauses)
        sql_columns = ", ".join(literal_objects(query_values.columns))
        sql_set_columns = ", ".join([f"t.{field} = s.{field}" for field in query_values.columns])
        sql_select_columns = ", ".join(literal_objects(query_values.columns, alias="s"))
        sql = (
            "SET XACT_ABORT ON;"
            + f"\nWITH s AS (SELECT {sql_columns}\nFROM (VALUES {query_values.sql}) AS ({sql_columns}));"
            + f"\nUPDATE t SET {sql_set_columns}\nFROM {cls.query_builder.full_table_name} t"
            + f"\nJOIN s ON {query_conflict_conditions.sql}"
            + f"\nINSERT INTO {cls.query_builder.full_table_name} ({sql_columns})"
            + f"\nSELECT {sql_select_columns}\nFROM s\nWHERE NOT EXISTS (SELECT 1 FROM {cls.query_builder.full_table_name} t WHERE {query_conflict_conditions.sql})"
        )
        return SqlQuery(sql=sql, params=query_values.params, columns=query_values.params)

    @classmethod
    def update(
        cls,
        records: List[T] | pd.DataFrame,
        update_conditions: SqlConditionInterface,
        returning: bool,
        text_clauses: Dict[str, SqlText],
    ):
        if len(records) == 0:
            raise ValueError("[ERROR][REPO]: Empty records")
        query_update_conditions = cls.query_builder.where(conditions=update_conditions)
        query_values = cls.query_builder.values(records, text_clauses=text_clauses)
        sql_columns = ", ".join(literal_objects(query_values.columns))
        sql_set_columns = ", ".join([f"t.{field} = s.{field}" for field in query_values.columns])
        sql_returning = "\nOUTPUT INSERTED.*" if returning else ""
        sql = (
            f"UPDATE {cls.query_builder.full_table_name} t SET {sql_set_columns}\n"
            + sql_returning
            + f"FROM (VALUES {query_values.sql}) AS ({sql_columns})\n"
            + f"WHERE {query_update_conditions.sql}"
        )
        return SqlQuery(sql=sql, params=query_values.params, columns=query_values.params)
