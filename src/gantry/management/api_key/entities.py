from typing import TypedDict


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
