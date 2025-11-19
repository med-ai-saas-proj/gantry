from typing import TypedDict


class JwtPayload(TypedDict):
    sub: str
    name: str


class AuthInfo(TypedDict):
    id: str
    username: str


class TokenInfo(TypedDict):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    refresh_token_expires_in: int
