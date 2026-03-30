from src.shared.dtos.base import BaseDTO

from datetime import datetime

from pydantic import Field


class ApiKeyWriteRequest(BaseDTO):
    """Input DTO for creating or updating an API key."""

    name: str = Field(min_length=1, max_length=1024)
    description: str = Field(default="", max_length=4096)
    permissions: list[str] = Field(default_factory=list)


class ApiKeyResponse(BaseDTO):
    """Output DTO for one API key resource."""

    id: int
    project_id: str
    name: str
    description: str
    hint: str
    created_at: datetime
    permissions: list[str]
    disabled: bool


class ApiKeyCreateResponse(ApiKeyResponse):
    """Create response that includes the raw key once."""

    key: str


class ApiKeyListResponse(BaseDTO):
    """List response for project API keys."""

    total: int
    results: list[ApiKeyResponse]


class ApiKeyPermissionCatalogResponse(BaseDTO):
    """List all permissions currently available to API keys."""

    total: int
    results: list[str]
    finalized: bool


class ApiKeyPermissionAuditResponse(BaseDTO):
    """Describe mismatches between runtime and stored API key permissions."""

    registered_permissions: list[str]
    stored_permissions: list[str]
    stale_permissions: list[str]
    unused_permissions: list[str]
