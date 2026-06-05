from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt

from tests.settings import KEYCLOAK_URL, REALM


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def password_token(
    username: str,
    password: str,
    client_id: str,
    *,
    scope: str = "openid profile email",
    keycloak_url: str = KEYCLOAK_URL,
    realm: str = REALM,
) -> dict[str, Any]:
    """Request a password-grant token from the configured identity provider."""
    response = httpx.post(
        f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token",
        data={
            "client_id": client_id,
            "username": username,
            "password": password,
            "grant_type": "password",
            "scope": scope,
        },
        timeout=12.0,
    )
    response.raise_for_status()
    return response.json()


def token_claims(token: str) -> dict[str, Any]:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def forge_jwt(
    claims: dict[str, Any] | None = None,
    *,
    secret: str = "test-secret",
    algorithm: str = "HS256",
    expires_in_seconds: int = 300,
) -> str:
    now = datetime.now(tz=UTC)
    payload = {
        "sub": "user-1",
        "name": "api-user",
        "email": "api-user@example.com",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
        "realm_access": {"roles": []},
        "organization": {"id": "org-1"},
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_forged_jwt(
    token: str,
    *,
    secret: str = "test-secret",
    algorithms: list[str] | None = None,
) -> dict[str, Any]:
    return jwt.decode(
        token,
        secret,
        algorithms=algorithms or ["HS256"],
        options={"verify_aud": False},
    )
