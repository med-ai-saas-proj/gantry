"""This file contain definition of ${app_name}'s repositories."""

from . import entities

from gantry.db.postgres.repository import PostgresRepo
from gantry.db.postgres.query_builder import PostgresQueryBuilder


class ExampleRepo(PostgresRepo[entities.Example]):
    query_builder = PostgresQueryBuilder(table="example_table", schema=None)
    JSON_FIELDS = []
