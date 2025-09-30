from src.shared.custom_types.base import BaseDict

from .query_builder import (
    SqlText,
    SqlQuery,
    BaseSqlQueryBuilder,
    SqlConditionInterface,
    literal_object,
    literal_objects,
)

import json
from abc import ABC
from typing import Generic, TypeVar

import pandas as pd


T = TypeVar("T", bound=BaseDict)


class BaseRepo(ABC, Generic[T]):
    @classmethod
    def dump_records(cls, records: list[T]) -> list[T]: ...

    @classmethod
    def data_frame_factory(cls, cur) -> pd.DataFrame: ...

    @classmethod
    def row_factory(cls, cur) -> list[T]: ...

    @classmethod
    def get_all(cls) -> SqlQuery: ...

    @classmethod
    def insert_many(
        cls,
        records: list[T | BaseDict] | pd.DataFrame,
        returning: bool,
        execute_batch=False,
        text_clauses: dict[str, SqlText] | None = None,
    ) -> SqlQuery: ...

    @classmethod
    def insert(cls, record: T | BaseDict, returning: bool) -> SqlQuery: ...

    @classmethod
    def insert_on_conflict_do_nothing(
        cls, record: T | BaseDict, identity_columns: list[str], returning: bool
    ) -> SqlQuery: ...

    @classmethod
    def update_many(
        cls,
        records: list[T] | pd.DataFrame | list[BaseDict],
        identity_columns: list[str],
        returning: bool,
        text_clauses: dict[str, SqlText] | None = None,
        execute_batch=False,
    ) -> SqlQuery: ...

    @classmethod
    def update(
        cls,
        record: T | BaseDict,
        identity_columns: list[str],
        returning: bool,
        text_clauses: dict[str, SqlText] | None = None,
    ) -> SqlQuery: ...

    @classmethod
    def get_by_condition(
        cls, conditions: SqlConditionInterface
    ) -> SqlQuery: ...

    @classmethod
    def get_by_id(cls, _id: int):
        conditions: SqlConditionInterface = {
            "logical": "and",
            "conditions": [{"field": "id", "operator": "=", "value": _id}],
        }
        return cls.get_by_condition(conditions=conditions)

    @classmethod
    def delete_by_condition(
        cls, conditions: SqlConditionInterface, returning: bool
    ) -> SqlQuery: ...

    @classmethod
    def delete_by_id(cls, _id: int):
        conditions: SqlConditionInterface = {
            "logical": "and",
            "conditions": [{"field": "id", "operator": "=", "value": _id}],
        }
        return cls.get_by_condition(conditions=conditions)

    @classmethod
    def lock_table(cls, mode) -> SqlQuery: ...
