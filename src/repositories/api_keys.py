from src.entities.api_key import ApiKey
from src.query_builders.postgres import BaseQueryBuilder
from src.repositories.postgres import PostgresRepo


class ApiKeyRepo(PostgresRepo[ApiKey]):
    query_builder = BaseQueryBuilder(table="api_keys", schema=None)
    JSON_FIELDS = []
