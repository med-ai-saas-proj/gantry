from src.shared.consts import messages_const
from src.shared.custom_types.error_exception import RecoverableError

from .entities import UserInfo
from .settings import AuthSetting

from typing import Any, Callable, final

import jwt
from jwt import PyJWKClient
from safe_result import Ok, Err, Result


class UnauthorizedError(RecoverableError):
    status = 401
    code = "unauthorized"
    title = messages_const.UNAUTHORIZED


class KeycloakService:
    def __init__(self, server_url: str, realm: str, client_id: str):
        # Strip trailing slash from server URL
        self.server_url = server_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id

        self.jwks_url = f"{self.server_url}/realms/{self.realm}/protocol/openid-connect/certs"
        self.issuer = f"{self.server_url}/realms/{self.realm}"
        self.client_id = client_id

        self.jwk_client = PyJWKClient(self.jwks_url, cache_keys=True)

    def verify_token(self, token: str) -> Result[UserInfo, UnauthorizedError]:
        """Verify Keycloak JWT token"""
        try:
            # Get the signing key from the token header
            signing_key = self.jwk_client.get_signing_key_from_jwt(token)

            # Decode and verify the token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience="account",
                issuer=self.issuer,
                options={
                    "verify_exp": True,
                    # "verify_iss": True,
                    # "verify_aud": True,
                    "verify_iss": False,
                    "verify_aud": False,
                },
            )

            return self._map_claims_to_auth_info(payload)

        except Exception as e:
            return Err(UnauthorizedError(from_exception=e))

    def _map_claims_to_auth_info(
        self, claims: dict[str, Any]
    ) -> Result[UserInfo, UnauthorizedError]:
        """Maps Keycloak JWT claims to the internal AuthInfo entity.
        Keycloak always includes 'sub' as the user UUID.
        """
        user_id = claims.get("sub")
        if not isinstance(user_id, str):
            return Err(
                UnauthorizedError(
                    from_exception=ValueError(
                        f"User id not found or is not a string, {user_id=}"
                    )
                )
            )

        def tryNone[T](fn: Callable[[], T]) -> T | None:
            try:
                return fn()
            except:
                return None

        # Extract roles from multiple sources in JWT
        roles: list[str] = []
        
        # Realm roles (from realm_access.roles)
        realm_roles = tryNone(
            lambda: claims.get("realm_access", {}).get("roles", [])
        )
        if realm_roles:
            roles.extend(realm_roles)
        
        # Client roles (from resource_access.{client_id}.roles)
        # Get roles from the management client
        client_roles = tryNone(
            lambda: claims.get("resource_access", {})
                          .get(self.client_id, {})
                          .get("roles", [])
        )
        if client_roles:
            roles.extend(client_roles)
        
        # Also check account client roles for backwards compatibility
        account_roles = tryNone(
            lambda: claims.get("resource_access", {})
                          .get("account", {})
                          .get("roles", [])
        )
        if account_roles:
            roles.extend(account_roles)

        auth_info: UserInfo = {
            "id": claims["sub"],
            "username": claims.get("preferred_username"),
            "email": claims.get("email"),
            "roles": roles if roles else None,
        }

        return Ok(auth_info)