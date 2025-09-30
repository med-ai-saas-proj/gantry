from src.db.postgres.repository import PostgresRepo
from src.db.postgres.query_builder import PostgresQueryBuilder

from ..entities.user import User


class UserRepo(PostgresRepo[User]):
    query_builder = PostgresQueryBuilder(table="users", schema=None)
    JSON_FIELDS = []
