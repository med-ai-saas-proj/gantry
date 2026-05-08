from typing import TypedDict


class ApiKeyInfo(TypedDict):
    """Represents authenticated API key context for downstream services."""

    api_key_id: int
    api_key_uuid: str
    project_id: int
    project_uuid: str
    org_id: str
    organization_uuid: str
    user_uuid: str
    hashed_key: str
    permissions: list[str]
    rpm_limit_organization: int
    rpm_limit_project: int
    spending_limit_organization: int
    spending_limit_project: int


class ApiKeyContextRecord(TypedDict):
    """Internal storage/cache record used before final request mapping."""

    api_key_id: int
    api_key_uuid: str
    project_id: int
    project_uuid: str
    org_id: str
    organization_uuid: str
    user_uuid: str
    hashed_key: str
    permissions: list[str]
    disabled: bool
    rpm_limit_organization: int
    rpm_limit_project: int
    spending_limit_organization: int
    spending_limit_project: int
