# src/auth/services/keycloak.py
from src.auth.settings import AuthSetting
from src.shared.consts import messages_const
from src.auth.entities.auth_info import AuthInfo
from src.shared.custom_types.error_exception import RecoverableError

from typing import Any

import jwt
from jwt import (
    PyJWKClient,
    InvalidTokenError,
    InvalidIssuerError,
    InvalidAudienceError,
    ExpiredSignatureError,
)


class UnauthorizedError(RecoverableError):
    status = 401
    title = messages_const.UNAUTHORIZED


class KeycloakService:
    def __init__(self, settings: AuthSetting):
        self.settings = settings

        # Strip trailing slash from server URL
        server_url = settings.keycloak_server_url.rstrip("/")
        realm = settings.keycloak_realm
        client_id = settings.keycloak_client_id

        self.jwks_url = (
            f"{server_url}/realms/{realm}/protocol/openid-connect/certs"
        )
        self.issuer = f"{server_url}/realms/{realm}"
        self.client_id = client_id

        try:
            self.jwk_client = PyJWKClient(self.jwks_url, cache_keys=True)
        except Exception:
            raise

    def verify_token(self, token: str) -> AuthInfo:
        """Verify Keycloak JWT token"""
        try:
            # Get the signing key from the token header
            signing_key = self.jwk_client.get_signing_key_from_jwt(token)

            # Decode and verify the token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
            )

            return self._map_claims_to_auth_info(payload)

        except ExpiredSignatureError:
            raise UnauthorizedError()
        except InvalidAudienceError:
            raise UnauthorizedError()
        except InvalidIssuerError:
            raise UnauthorizedError()
        except InvalidTokenError:
            raise UnauthorizedError()
        except Exception:
            raise UnauthorizedError()

    def _map_claims_to_auth_info(self, claims: dict[str, Any]) -> AuthInfo:
        """Maps Keycloak JWT claims to the internal AuthInfo entity.
        Keycloak always includes 'sub' as the user UUID.
        """
        try:
            user_id = claims.get("sub")
            if not user_id:
                raise ValueError("Token missing required 'sub' claim")

            # Create AuthInfo as a Pydantic model
            auth_info = AuthInfo(
                id=str(user_id),
                email=claims.get("email"),
                username=claims.get("preferred_username"),
            )

            return auth_info
        except Exception:
            raise
