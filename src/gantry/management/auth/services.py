"""Authentication and authorization services for management API."""

from pyrusult import Ok, Err, Result, ResultStatus
from gantry.keycloak import KeycloakServiceClient
from gantry.shared.consts import messages_const
from gantry.shared.custom_types.error_exception import RecoverableError

from .entities import UserInfo, AdminInfo

from typing import Any

import jwt
from jwt import PyJWKClient
from keycloak import KeycloakOpenID


class UnauthorizedError(RecoverableError):
    status = 401
    code = "unauthorized"
    title = messages_const.UNAUTHORIZED


class MissingOrganizationClaimError(UnauthorizedError):
    """Raised when a regular user token has no organization claim."""

    code = "missing_organization_claim"
    detail = "The authenticated token does not include an organization claim."


class ForbiddenError(RecoverableError):
    """Raised when user doesn't have required permissions."""

    status = 403
    code = "forbidden"
    title = "Forbidden"
    detail = "You don't have permission to perform this action."


class InsufficientPermissionsError(ForbiddenError):
    """Raised when user lacks specific role permissions."""

    def __init__(self, required_roles: list[str]):
        super().__init__()
        roles_str = ", ".join(required_roles)
        self.detail = f"Insufficient permissions. Required roles: {roles_str}"


class InvalidClientTokenError(ForbiddenError):
    """Raised when a token was issued for a different Keycloak client."""

    code = "invalid_client_token"
    title = "Invalid Client Token"

    def __init__(self, expected_client_id: str, actual_client_id: str | None):
        super().__init__()
        actual = actual_client_id or "<missing>"
        self.detail = (
            "Token was issued for an unexpected Keycloak client. "
            f"Expected {expected_client_id}, got {actual}."
        )


class AuthService:
    """Authentication and authorization service.

    Handles token verification and role-based access control.
    """

    ADMIN_REALM_ROLE = "ADMIN"

    def __init__(
        self,
        server_url: str,
        realm: str,
        client_id: str,
        keycloak_client: KeycloakServiceClient,
        require_organization_claim: bool = True,
        forbidden_realm_roles: set[str] | None = None,
        issuer_url: str | None = None,
        jwks_url: str | None = None,
    ):
        # Strip trailing slash from server URL
        self.server_url = server_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.require_organization_claim = require_organization_claim
        self.forbidden_realm_roles = forbidden_realm_roles or set()
        self.keycloak_client = keycloak_client

        self._default_jwks_url = (
            f"{self.server_url}/realms/{self.realm}"
            f"/protocol/openid-connect/certs"
        )
        self._default_issuer = f"{self.server_url}/realms/{self.realm}"
        self._issuer_url = issuer_url.rstrip("/") if issuer_url else None
        self._jwks_url = jwks_url.rstrip("/") if jwks_url else None
        self._openid_client = KeycloakOpenID(
            server_url=self.server_url,
            realm_name=self.realm,
            client_id=self.client_id,
            verify=True,
        )
        self._openid_metadata: dict[str, Any] | None = None
        self._jwk_client: PyJWKClient | None = None
        self._jwk_client_url: str | None = None

    def _getOpenIdMetadata(self) -> dict[str, Any]:
        """Load and cache OpenID metadata via python-keycloak."""
        if self._openid_metadata is not None:
            return self._openid_metadata
        try:
            metadata = self._openid_client.well_known()
            if isinstance(metadata, dict):
                self._openid_metadata = metadata
                return metadata
        except Exception:
            pass
        self._openid_metadata = {}
        return self._openid_metadata

    def _getIssuer(self) -> str:
        """Return the issuer using the configured server_url.

        In production, Keycloak often issues tokens with a public hostname
        while the backend reaches JWKS through the internal network. In that
        case issuer_url should be configured explicitly.
        """
        return self._issuer_url or self._default_issuer

    def _getJwksUrl(self) -> str:
        """Return the JWKS URL used by the backend.

        Defaults to the internal server_url. Configure jwks_url explicitly
        when the backend should fetch keys from a different address.
        """
        return self._jwks_url or self._default_jwks_url

    def _getJwkClient(self) -> PyJWKClient:
        """Get a cached PyJWKClient bound to the resolved JWKS URL."""
        jwks_url = self._getJwksUrl()
        if self._jwk_client is None or self._jwk_client_url != jwks_url:
            self._jwk_client = PyJWKClient(jwks_url, cache_keys=True)
            self._jwk_client_url = jwks_url
        return self._jwk_client

    def _ensureAuthorizedClient(
        self, claims: dict[str, Any]
    ) -> Result[bool, InvalidClientTokenError]:
        """Ensure the access token was minted for this API client path."""
        actual_client_id = claims.get("azp")
        if actual_client_id != self.client_id:
            return Err(
                InvalidClientTokenError(
                    self.client_id,
                    actual_client_id
                    if isinstance(actual_client_id, str)
                    else None,
                )
            )
        return Ok(True)

    def _realmRoles(self, claims: dict[str, Any]) -> set[str]:
        realm_access = claims.get("realm_access")
        if not isinstance(realm_access, dict):
            return set()
        roles = realm_access.get("roles")
        if not isinstance(roles, list):
            return set()
        return {role for role in roles if isinstance(role, str)}

    def _ensureAllowedRealmRoles(
        self, claims: dict[str, Any]
    ) -> Result[bool, ForbiddenError]:
        """Reject tokens with realm roles that are forbidden on this surface."""
        if self.forbidden_realm_roles.intersection(self._realmRoles(claims)):
            return Err(ForbiddenError())
        return Ok(True)

    async def verifyToken(
        self, token: str
    ) -> Result[
        UserInfo, UnauthorizedError | ForbiddenError | InvalidClientTokenError
    ]:
        """Verify Keycloak JWT token."""
        try:
            # Get the signing key from the token header
            signing_key = self._getJwkClient().get_signing_key_from_jwt(token)

            # Decode and verify the token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience="account",
                issuer=self._getIssuer(),
                options={
                    "verify_exp": True,
                    # "verify_aud": True,
                    "verify_iss": False,
                    "verify_aud": False,
                },
            )

            client_res = self._ensureAuthorizedClient(payload)
            if client_res.status == ResultStatus.Err:
                return client_res.into()

            role_res = self._ensureAllowedRealmRoles(payload)
            if role_res.status == ResultStatus.Err:
                return role_res.into()

            return await self._mapClaimsToAuthInfo(payload)

        except Exception as e:
            return Err(UnauthorizedError(from_exception=e))

    async def _mapClaimsToAuthInfo(
        self, claims: dict[str, Any]
    ) -> Result[UserInfo, UnauthorizedError]:
        """Maps Keycloak JWT claims to the internal AuthInfo entity.

        Keycloak always includes 'sub' as the user UUID.
        """
        user_uuid = claims.get("sub")
        if not isinstance(user_uuid, str):
            return Err(
                UnauthorizedError(
                    from_exception=ValueError(
                        f"User uuid not found or is not a string, {user_uuid=}"
                    )
                )
            )

        username = claims.get("name")

        other_attributes = (
            await self.keycloak_client.getUserAttributes(claims["sub"])
        ).unwrap()
        org_id = await self._resolveOrganizationId(claims)
        if self.require_organization_claim and org_id is None:
            return Err(MissingOrganizationClaimError())

        auth_info: UserInfo = {
            "id": claims["sub"],
            "username": username if isinstance(username, str) else None,
            "email": claims.get("email"),
            "org_uuid": org_id or "",
            "org_permissions": other_attributes.get("org_permissions", []),
            "project_permissions": other_attributes.get(
                "project_permissions", {}
            ),
        }

        return Ok(auth_info)

    async def _resolveOrganizationId(
        self, claims: dict[str, Any]
    ) -> str | None:
        """Resolve organization id from token claims, then Keycloak membership."""
        org_id = self._extractOrganizationId(claims.get("organization"))
        if org_id is not None:
            return org_id

        if not self.require_organization_claim:
            return None

        orgs_res = await self.keycloak_client.getMemberOrganizations(
            claims["sub"]
        )
        if orgs_res.status == ResultStatus.Err:
            orgs_res.unwrap()

        org_ids = {
            str(org.get("id"))
            for org in orgs_res.unwrap()
            if isinstance(org, dict) and org.get("id")
        }
        if len(org_ids) == 1:
            return next(iter(org_ids))
        return None

    def _extractOrganizationId(self, organization_claim: Any) -> str | None:
        """Extract an organization id from supported Keycloak claim shapes."""
        # Older mapper setups can emit a single organization string directly.
        if isinstance(organization_claim, str):
            return organization_claim or None

        # Multivalued claims are returned as a list; use the first non-empty value.
        if isinstance(organization_claim, list):
            for value in organization_claim:
                if isinstance(value, str) and value:
                    return value
            return None

        # The current mapper can emit an object keyed by org name with nested ids.
        if isinstance(organization_claim, dict):
            direct_id = organization_claim.get("id")
            if isinstance(direct_id, str) and direct_id:
                return direct_id

            # Some Keycloak shapes nest the id one level deeper under each org entry.
            for value in organization_claim.values():
                if isinstance(value, dict):
                    nested_id = value.get("id")
                    if isinstance(nested_id, str) and nested_id:
                        return nested_id

        return None

    def verifyTokenAdmin(
        self, token: str
    ) -> Result[AdminInfo, UnauthorizedError | ForbiddenError]:
        try:
            signing_key = self._getJwkClient().get_signing_key_from_jwt(token)

            # Decode and verify the token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience="account",
                issuer=self._getIssuer(),
                options={
                    "verify_exp": True,
                    # "verify_aud": True,
                    "verify_iss": False,
                    "verify_aud": False,
                },
            )

            client_res = self._ensureAuthorizedClient(payload)
            if client_res.status == ResultStatus.Err:
                return client_res.into()

            if self.ADMIN_REALM_ROLE not in self._realmRoles(payload):
                return Err(ForbiddenError())

            return Ok(
                AdminInfo(
                    id=payload.get("sub", ""),
                    username=payload.get("name", ""),
                    email=payload.get("email", ""),
                )
            )
        except Exception as e:
            return Err(UnauthorizedError(from_exception=e))
