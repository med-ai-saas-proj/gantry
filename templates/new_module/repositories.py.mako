"""This file contain definition of ${app_name}'s repositories."""

from src.db.postgres.repository import PostgresRepo
from src.db.postgres.query_builder import PostgresQueryBuilder

from . import entities


class ExampleRepo(PostgresRepo[entities.Example]):
    query_builder = PostgresQueryBuilder(table="example_table", schema=None)
    JSON_FIELDS = []
