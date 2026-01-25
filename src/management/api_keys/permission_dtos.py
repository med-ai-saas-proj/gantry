"""DTOs for Permission management."""

from src.shared.dtos.base import BaseDTO

from datetime import datetime
from pydantic import Field


class CreatePermissionInput(BaseDTO):
    """Input DTO for creating a permission."""

    name: str = Field(..., description="Unique permission name")
    description: str = Field(..., description="Permission description")


class UpdatePermissionInput(BaseDTO):
    """Input DTO for updating a permission."""

    description: str = Field(..., description="Updated permission description")


class PermissionOutput(BaseDTO):
    """Output DTO for permission details."""

    id: int
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class PermissionListOutput(BaseDTO):
    """Output DTO for listing permissions."""

    permissions: list[PermissionOutput]
    total: int
