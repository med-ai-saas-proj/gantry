from src.db_v2.base import (
    BaseEntity,
    TableColumns,
    TimestampsFields,
    metadata,
    timestamps,
)
from src.db_v2.repository import Repository

import uuid
from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy import (
    UUID,
    Table,
    Column,
    String,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
)


ApiKeyPermissions = Table(
    "api_key_permissions",
    metadata,
    Column("api_key_id", UUID, primary_key=True),
    Column("permission_name", String, primary_key=True),
    ForeignKeyConstraint(["api_key_id"], ["api_keys.id"]),
    ForeignKeyConstraint(["permission_name"], ["permissions.name"]),
)


ApiKeys = Table(
    "api_keys",
    metadata,
    Column("id", UUID, primary_key=True, unique=True, nullable=False),
    Column("owner_id", UUID, ForeignKey("users.id"), nullable=False),
    Column("hashed_key", String, unique=True, nullable=False),
    Column("expiration_date", DateTime, nullable=True),
    *timestamps(),
)

Permissions = Table(
    "permissions",
    metadata,
    Column("name", String, primary_key=True, unique=True, nullable=False),
    Column("description", String, nullable=True),
    *timestamps(),
)


class ApiKeyPermissionRepo(Repository):
    class TableColumns:
        api_key_id: Column[uuid.UUID] = ApiKeyPermissions.c.api_key_id
        permission_name: Column[str] = ApiKeyPermissions.c.permission_name

    table = ApiKeyPermissions
    c = TableColumns
    entity_type = None  # No specific entity class for this association table


@dataclass(kw_only=True)
class ApiKey(BaseEntity, TimestampsFields):
    id: Optional[str] = None

    owner_id: Optional[str]
    hashed_key: str
    expiration_date: Optional[datetime]


class ApiKeyRepo(Repository[ApiKey, str]):
    class TableColumns(TableColumns):
        id: Column[str] = ApiKeys.c.id
        owner_id: Column[str] = ApiKeys.c.owner_id
        hashed_key: Column[str] = ApiKeys.c.hashed_key
        expiration_date: Column[DateTime] = ApiKeys.c.expiration_date
        created_at: Column[DateTime] = ApiKeys.c.created_at
        updated_at: Column[DateTime] = ApiKeys.c.updated_at

    table = ApiKeys
    c = TableColumns
    entity_type = ApiKey


@dataclass(kw_only=True)
class Permission(BaseEntity, TimestampsFields):
    __key__ = "name"
    name: str
    description: Optional[str]


class PermissionRepo(Repository[Permission, str]):
    class TableColumns(TableColumns):
        __key__ = "name"
        name: Column[str] = Permissions.c.name
        description: Column[Optional[str]] = Permissions.c.description
        created_at: Column[DateTime] = Permissions.c.created_at
        updated_at: Column[DateTime] = Permissions.c.updated_at

    table = Permissions
    c = TableColumns
    entity_type = Permission
