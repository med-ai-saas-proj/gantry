from src.db_v2.base import BaseSQLModel, naming_convention
from src.db_v2.initialize import async_engine

from sqlalchemy import MetaData


class AuthBaseSQLModel(BaseSQLModel):
    """Base SQL Model for this module only."""

    __abstract__ = True

    metadata = MetaData("Auth", naming_convention=naming_convention)
