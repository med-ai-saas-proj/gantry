from src.shared.dtos.base import BaseDTO
from src.shared.dtos.error_output import ProblemDetails

from typing import Literal, TypedDict

from pydantic import Field, EmailStr, SecretStr


class LoginInput(BaseDTO):
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=24)


class LoginOutputSuccess(TypedDict):
    access_token: str
    token_type: Literal["Bearer"]
    expire_in: int
    refresh_token: str


class CrateAPIKeyInput(BaseDTO):
    name: str | None
    project_id: str
    permissions: list[str]


class CrateAPIKeyOutputSuccess(TypedDict):
    key: str
