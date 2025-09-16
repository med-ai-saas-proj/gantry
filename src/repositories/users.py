from src.entities import User
from src.query_builders.postgres import BaseQueryBuilder
from src.repositories.postgres import PostgresRepo


class UserRepo(PostgresRepo[User]):
    query_builder = BaseQueryBuilder(table="users", schema=None)
    JSON_FIELDS = []
