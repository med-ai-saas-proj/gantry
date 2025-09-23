from .base import BaseDTO
from pydantic import Field, field_validator
from typing import List, Optional


class CreateApiKeyRequestDTO(BaseDTO):
    name: str = Field(
        ..., min_length=1, max_length=255, description="Name for the API key"
    )
    expires_in_days: Optional[int] = Field(
        None, ge=1, le=365, description="Expiration in days (optional)"
    )

    @field_validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("API key name cannot be empty")
        return v.strip()


class CreateApiKeyResponseDTO(BaseDTO):
    id: str = Field(..., description="API key ID")
    name: str = Field(..., description="API key name")
    api_key: str = Field(
        ..., description="The actual API key (only returned once)"
    )
    is_active: bool = Field(..., description="Whether the API key is active")
    expires_at: Optional[str] = Field(None, description="Expiration date")
    created_at: str = Field(..., description="Creation date")


class ApiKeyInfoDTO(BaseDTO):
    """Individual API key information (without the actual key)"""

    id: str = Field(..., description="API key ID")
    name: str = Field(..., description="API key name")
    is_active: bool = Field(..., description="Whether the API key is active")
    last_used_at: Optional[str] = Field(
        None, description="Last time the API key was used"
    )
    expires_at: Optional[str] = Field(None, description="Expiration date")
    created_at: str = Field(..., description="Creation date")
    updated_at: str = Field(..., description="Last update date")


class ApiKeyListResponseDTO(BaseDTO):
    """Response containing a list of user's API keys"""

    api_keys: List[ApiKeyInfoDTO] = Field(
        ..., description="List of user's API keys"
    )
    total_count: int = Field(..., description="Total number of API keys")
