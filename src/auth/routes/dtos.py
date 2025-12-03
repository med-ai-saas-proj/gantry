"""Data Transfer Objects for Authentication Module."""

from src.shared.dtos.base import BaseDTO

from typing import Literal, TypedDict

from pydantic import Field, EmailStr, SecretStr


class LoginRequest(BaseDTO):
    """Input DTO for user login."""

    grant_type: Literal["password"]
    username: EmailStr
    password: SecretStr = Field(..., description="User's password")


class RefreshAccessTokenRequest(BaseDTO):
    """Input DTO for refreshing access token."""

    grant_type: Literal["refresh_token"]
    refresh_token: str


class LoginSuccessResponse(TypedDict):
    """Output DTO for successful login."""

    access_token: str
    token_type: Literal["Bearer"]
    expire_in: int
    refresh_token: str
    refresh_token_expires_in: int


class CreateAPIKeyRequest(BaseDTO):
    """Input DTO for creating an API key."""

    name: str | None
    project_id: str
    permissions: list[str]


class CreateAPIKeySuccessResponse(TypedDict):
    """Output DTO for successful API key creation."""

    key: str


class RefreshAccessTokenSuccessResponse(TypedDict):
    """Output DTO for successful access token refresh."""

    access_token: str
    token_type: Literal["Bearer"]
    expires_in: int


class LogoutRequest(BaseDTO):
    """Input DTO for user logout."""

    refresh_token: str = Field(..., description="Revoked refresh token")
