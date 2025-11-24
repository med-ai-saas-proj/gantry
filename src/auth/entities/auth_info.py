from typing import TypedDict, NotRequired


class JwtPayload(TypedDict):
    sub: str
    email: str
    exp: NotRequired[str]


class AuthInfo(TypedDict):
    id: str
    email: str


class TokenInfo(TypedDict):
    access_token: str
    expires_in: int
    refresh_token: NotRequired[str]
    refresh_token_expires_in: NotRequired[int]
