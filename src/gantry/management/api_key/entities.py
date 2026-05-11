from typing import TypedDict
from datetime import datetime


class ApiKeyInfo(TypedDict):
    """Represents authenticated API key context for downstream services."""

    api_key_id: int
    api_key_uuid: str
    project_id: int
    project_uuid: str
    organization_uuid: str
    user_uuid: str
    hashed_key: str
    permissions: list[str]
    rpm_limit_organization: int | None
    rpm_limit_project: int | None
    spending_limit_organization: int | None
    spending_limit_project: int | None


class ApiKeyContextRecord(TypedDict):
    """Internal storage/cache record used before final request mapping."""

    api_key_id: int
    api_key_uuid: str
    project_id: int
    project_uuid: str
    organization_uuid: str
    user_uuid: str
    hashed_key: str
    permissions: list[str]
    disabled: bool
    rpm_limit_organization: int | None
    rpm_limit_project: int | None
    spending_limit_organization: int | None
    spending_limit_project: int | None


class ApiKeySnapshot(TypedDict):
    """Detached API key fields used outside an ORM session boundary."""

    api_key_id: int
    api_key_uuid: str
    project_id: int
    name: str
    description: str
    hint: str
    created_at: datetime
    permissions: list[str]
    disabled: bool
    hashed_key: str


class ApiKeyInternalIds(TypedDict):
    """Internal numeric ids resolved from a public API-key UUID."""

    api_key_id: int
    project_id: int
