"""Data transfer objects for authentication services."""

from typing import Literal, TypedDict, NotRequired


class JwtPayload(TypedDict):
    """The payload of a JWT token."""

    sub: str
    email: str
    exp: NotRequired[int]


class AuthInfo(TypedDict):
    """Represents authentication information about a user."""

    uid: str
    email: str


class LoginTokenData(TypedDict):
    """Returning of login service."""

    access_token: str
    expires_in: int
    token_type: Literal["Bearer"]
    refresh_token: str
    refresh_token_expires_in: int


class RefreshTokenData(TypedDict):
    """Returning of refresh token service."""

    access_token: str
    expires_in: int
    token_type: Literal["Bearer"]


class APIKeyInfo(TypedDict):
    """Represents information about an API key."""

    user_id: str
