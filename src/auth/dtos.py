from src.shared.dtos.base import BaseDTO

from datetime import datetime
from typing import Literal, TypedDict

from pydantic import Field, EmailStr, BaseModel, SecretStr


class LoginInput(BaseDTO):
    grant_type: Literal["password"]
    email: EmailStr
    password: SecretStr = Field(..., description="User's password")


class RefreshAccessTokenInput(BaseDTO):
    grant_type: Literal["refresh_token"]
    refresh_token: str


class LoginOutputSuccess(TypedDict):
    access_token: str
    token_type: Literal["Bearer"]
    expire_in: int
    refresh_token: str
    refresh_token_expires_in: int


class CreateAPIKeyInput(BaseDTO):
    name: str | None
    project_id: str
    permissions: list[str]


class CreateAPIKeyOutputSuccess(TypedDict):
    key: str


class ApiKeyResponse(TypedDict):
    id: str
    name: str | None
    is_active: bool
    expiration_date: datetime | None
    created_at: datetime | None


class UpdateApiKeyInput(BaseDTO):
    name: str | None = None
    is_active: bool | None = None


class RefreshAccessTokenOutputSuccess(TypedDict):
    access_token: str
    token_type: Literal["Bearer"]
    expires_in: int


class LogoutRequest(BaseDTO):
    refresh_token: str = Field(..., description="Revoked refresh token")
