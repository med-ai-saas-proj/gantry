from enum import Enum

from pydantic import BaseModel, Field


class GrantTypeEnum(Enum):
    Password = "password"


class EmailLoginRequest(BaseModel):
    grant_type: GrantTypeEnum = Field(
        ..., description="Grant Type, must be set to 'password'."
    )
    username: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = "bearer"
    expires_in: int


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error detail message")


class EmailRegisterRequest(BaseModel):
    username: str = Field(..., description="Desired username")
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class RegisterResponse(BaseModel):
    user_id: str = Field(..., description="Registered user ID")
    username: str = Field(..., description="Registered username")
