from typing import Literal, Optional, TypedDict, NotRequired

from pydantic import Field, BaseModel


class JwtPayload(TypedDict):
    sub: str
    email: str
    exp: NotRequired[int]


class AuthInfo(BaseModel):
    id: Optional[str] = Field(
        None, description="User ID (subject claim from token)"
    )
    email: Optional[str] = Field(None, description="User email")
    username: Optional[str] = Field(None, description="Username")


class TokenInfo(TypedDict):
    access_token: str
    expires_in: int
    token_type: Literal["Bearer"]
    refresh_token: NotRequired[str]
    refresh_token_expires_in: NotRequired[int]
