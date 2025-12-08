"""Base entity for SQLAlchemy models."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


naming_convention = {
    "ix": "idx_%(column_0_N_label)s",
    "uq": "%(table_name)s_%(column_0_N_name)s_uq",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}


class BaseSQLModel(MappedAsDataclass, DeclarativeBase, kw_only=True):
    """This should be the base of all SQL model."""

    metadata = MetaData(naming_convention=naming_convention)
    pass
