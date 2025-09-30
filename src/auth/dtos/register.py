from src.shared.dtos.base import BaseDTO

from pydantic import Field, EmailStr, field_validator


class RegisterRequestDTO(BaseDTO):
    email: EmailStr = Field(..., description="User Email Address")
    password: str = Field(
        ..., min_length=8, max_length=128, description="User password"
    )

    @field_validator("password")
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError(
                "Password must contain at least one uppercase letter"
            )
        if not any(c.islower() for c in v):
            raise ValueError(
                "Password must contain at least one lowercase letter"
            )
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class RegisterResponseDTO(BaseDTO):
    id: str
    email: str
    created_at: str


class ChangePasswordRequestDTO(BaseDTO):
    current_password: str = Field(
        ..., min_length=8, max_length=128, description="Current password"
    )
    new_password: str = Field(
        ..., min_length=8, max_length=128, description="New password"
    )

    @field_validator("new_password")
    def validate_new_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError(
                "New password must contain at least one uppercase letter"
            )
        if not any(c.islower() for c in v):
            raise ValueError(
                "New password must contain at least one lowercase letter"
            )
        if not any(c.isdigit() for c in v):
            raise ValueError("New password must contain at least one digit")
        return v


class LoginRequestDTO(BaseDTO):
    email: EmailStr = Field(..., description="User Email Address")
    password: str = Field(
        ..., min_length=8, max_length=128, description="User password"
    )
