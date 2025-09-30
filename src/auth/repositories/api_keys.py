from src.db.postgres.repository import PostgresRepo
from src.db.postgres.query_builder import PostgresQueryBuilder

from ..entities.api_key import ApiKey


class ApiKeyRepo(PostgresRepo[ApiKey]):
    query_builder = PostgresQueryBuilder(table="api_keys", schema=None)
    JSON_FIELDS = []
