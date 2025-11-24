from typing import Literal, TypedDict, NotRequired


class JwtPayload(TypedDict):
    sub: str
    email: str
    exp: NotRequired[int]


class AuthInfo(TypedDict):
    id: str
    email: str


class TokenInfo(TypedDict):
    access_token: str
    expires_in: int
    token_type: Literal["Bearer"]
    refresh_token: NotRequired[str]
    refresh_token_expires_in: NotRequired[int]
