"""Data Transfer Objects for Authentication Module."""

from src.shared.dtos.base import BaseDTO

from typing import Literal, TypedDict

from pydantic import Field, EmailStr, SecretStr


class LoginInput(BaseDTO):
    """Input DTO for user login."""

    grant_type: Literal["password"]
    email: EmailStr
    password: SecretStr = Field(..., description="User's password")


class RefreshAccessTokenInput(BaseDTO):
    """Input DTO for refreshing access token."""

    grant_type: Literal["refresh_token"]
    refresh_token: str


class LoginOutputSuccess(TypedDict):
    """Output DTO for successful login."""

    access_token: str
    token_type: Literal["Bearer"]
    expire_in: int
    refresh_token: str
    refresh_token_expires_in: int


class CreateAPIKeyInput(BaseDTO):
    """Input DTO for creating an API key."""

    name: str | None
    project_id: str
    permissions: list[str]


class CreateAPIKeyOutputSuccess(TypedDict):
    """Output DTO for successful API key creation."""

    key: str


class RefreshAccessTokenOutputSuccess(TypedDict):
    """Output DTO for successful access token refresh."""

    access_token: str
    token_type: Literal["Bearer"]
    expires_in: int


class LogoutRequest(BaseDTO):
    """Input DTO for user logout."""

    refresh_token: str = Field(..., description="Revoked refresh token")
