from src.db.base import BaseSQLModel


class AuthBaseSQLModel(BaseSQLModel):
    """Base SQL Model for this module only."""

    __abstract__ = True
    __table_args__ = {"schema": "Auth"}
