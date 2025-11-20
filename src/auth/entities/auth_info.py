from typing import TypedDict, NotRequired


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
