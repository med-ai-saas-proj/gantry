from src.db_v2.base import (
    BaseEntity,
    TableColumns,
    TimestampsFields,
    metadata,
    timestamps,
)
from src.db_v2.repository import Repository

from uuid import uuid4
from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy import UUID, Table, Column, String, Boolean


Users = Table(
    "users",
    metadata,
    Column(
        "id", UUID, primary_key=True, unique=True, nullable=False, default=uuid4
    ),
    Column("username", String, unique=True, nullable=False),
    Column("email", String, unique=True, nullable=False),
    Column("hashed_password", String, nullable=False),
    Column("is_active", Boolean, default=True),
    *timestamps(),
)


@dataclass(kw_only=True)
class User(BaseEntity, TimestampsFields):
    id: Optional[str] = None

    username: str
    email: str
    hashed_password: str
    is_active: bool = True


class UserRepo(Repository[User, str]):
    class TableColumns(TableColumns):
        id: Column[str] = Users.c.id
        username: Column[str] = Users.c.username
        email: Column[str] = Users.c.email
        hashed_password: Column[str] = Users.c.hashed_password
        is_active: Column[bool] = Users.c.is_active
        created_at: Column[datetime] = Users.c.created_at
        updated_at: Column[datetime] = Users.c.updated_at

    table = Users
    c = TableColumns
    entity_type = User
