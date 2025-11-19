from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class GrantTypeEnum(Enum):
    Password = "password"


class EmailLoginRequest(BaseModel):
    grant_type: Literal["password"] = Field(
        ..., description="Grant Type, must be set to 'password'."
    )
    username: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class RefreshTokenRequest(BaseModel):
    grant_type: Literal["refresh_token"] = Field(
        ..., description="Grant Type, must be set to 'refresh_token'."
    )
    refresh_token: str = Field(..., description="Refresh token")


class RefreshTokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str = Field(..., description="JWT refresh token")
    refresh_token_expires_in: int


class LogoutResponse(BaseModel):
    refresh_token: str = Field(..., description="Revoked refresh token")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error detail message")


class EmailRegisterRequest(BaseModel):
    username: str = Field(..., description="Desired username")
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class RegisterResponse(BaseModel):
    user_id: str = Field(..., description="Registered user ID")
    username: str = Field(..., description="Registered username")
