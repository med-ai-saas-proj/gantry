"""Authentication and authorization services for management API."""

from gantry.shared.consts import messages_const
from gantry.shared.utils.permission_utils import (
    normalize_project_permission_map,
)
from gantry.shared.custom_types.error_exception import RecoverableError

from .roles import (
    ManagementRole,
    has_role as _has_role,
    has_any_role as _has_any_role,
    has_all_roles as _has_all_roles,
)
from .entities import UserInfo

from typing import Any, Callable

import jwt
from jwt import PyJWKClient
from keycloak import KeycloakOpenID
from pyrusult import Ok, Err, Result


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


class AuthService:
    """
    Authentication and authorization service.

    Handles token verification and role-based access control.
    """

    ADMIN_REALM_ROLE = "ADMIN"

    def __init__(
        self,
        server_url: str,
        realm: str,
        client_id: str,
        require_organization_claim: bool = True,
    ):
        # Strip trailing slash from server URL
        self.server_url = server_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.require_organization_claim = require_organization_claim

        self._default_jwks_url = (
            f"{self.server_url}/realms/{self.realm}"
            f"/protocol/openid-connect/certs"
        )
        self._default_issuer = f"{self.server_url}/realms/{self.realm}"
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
        """Resolve the issuer from OpenID metadata with a safe fallback."""
        metadata = self._getOpenIdMetadata()
        issuer = metadata.get("issuer")
        if isinstance(issuer, str) and issuer:
            return issuer
        return self._default_issuer

    def _getJwksUrl(self) -> str:
        """Resolve the JWKS URL from OpenID metadata with a safe fallback."""
        metadata = self._getOpenIdMetadata()
        jwks_uri = metadata.get("jwks_uri")
        if isinstance(jwks_uri, str) and jwks_uri:
            return jwks_uri
        return self._default_jwks_url

    def _getJwkClient(self) -> PyJWKClient:
        """Get a cached PyJWKClient bound to the resolved JWKS URL."""
        jwks_url = self._getJwksUrl()
        if self._jwk_client is None or self._jwk_client_url != jwks_url:
            self._jwk_client = PyJWKClient(jwks_url, cache_keys=True)
            self._jwk_client_url = jwks_url
        return self._jwk_client

    def verifyToken(self, token: str) -> Result[UserInfo, UnauthorizedError]:
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
                    # "verify_iss": True,
                    # "verify_aud": True,
                    "verify_iss": False,
                    "verify_aud": False,
                },
            )

            return self._mapClaimsToAuthInfo(payload)

        except Exception as e:
            return Err(UnauthorizedError(from_exception=e))

    def _mapClaimsToAuthInfo(
        self, claims: dict[str, Any]
    ) -> Result[UserInfo, UnauthorizedError]:
        """Maps Keycloak JWT claims to the internal AuthInfo entity.

        Keycloak always includes 'sub' as the user UUID.
        """
        user_uid = claims.get("sub")
        if not isinstance(user_uid, str):
            return Err(
                UnauthorizedError(
                    from_exception=ValueError(
                        f"User uid not found or is not a string, {user_uid=}"
                    )
                )
            )

        def tryNone[T](fn: Callable[[], T]) -> T | None:
            try:
                return fn()
            except Exception:
                return None

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
            lambda: (
                claims.get("resource_access", {})
                .get(self.client_id, {})
                .get("roles", [])
            )
        )
        if client_roles:
            roles.extend(client_roles)

        # Also check account client roles for backwards compatibility
        account_roles = tryNone(
            lambda: (
                claims.get("resource_access", {})
                .get("account", {})
                .get("roles", [])
            )
        )
        if account_roles:
            roles.extend(account_roles)

        username = claims.get("preferred_username")

        org_id = self._extractOrganizationId(claims.get("organization"))
        if self.require_organization_claim and not org_id:
            return Err(MissingOrganizationClaimError())

        auth_info: UserInfo = {
            "id": claims["sub"],
            "username": username if isinstance(username, str) else None,
            "email": claims.get("email"),
            "roles": roles,
            "org_id": org_id or "",
            "project_ids": self._extractProjectIds(claims, roles) or [],
        }

        return Ok(auth_info)

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

    @staticmethod
    def _extractProjectIdsFromEntries(entries: list[str]) -> list[str]:
        """Extract distinct project uids from flat token entries like `proj:perm`."""
        seen: set[str] = set()
        project_uids: list[str] = []
        for entry in entries:
            project_uid, separator, permission = entry.partition(":")
            if not separator or not project_uid or not permission:
                continue
            if project_uid in seen:
                continue
            seen.add(project_uid)
            project_uids.append(project_uid)
        return project_uids

    def _extractProjectIds(
        self,
        claims: dict[str, Any],
        roles: list[str],
    ) -> list[str]:
        """Extract project uids directly from token-carried permission data."""
        grouped_permissions = normalize_project_permission_map(
            claims.get("project_permissions", {})
        )
        if grouped_permissions:
            return list(grouped_permissions)
        return self._extractProjectIdsFromEntries(roles)

    def checkAdminRole(
        self,
        user_info: UserInfo,
    ) -> Result[None, InsufficientPermissionsError]:
        """Require the Keycloak realm role `ADMIN` for admin-only flows."""
        if self.ADMIN_REALM_ROLE not in user_info.get("roles", []):
            return Err(InsufficientPermissionsError([self.ADMIN_REALM_ROLE]))
        return Ok(None)

    def checkRole(
        self, user_info: UserInfo, role: ManagementRole
    ) -> Result[None, InsufficientPermissionsError]:
        """
        Check if user has a specific role.

        Args:
            user_info: The authenticated user info
            role: The required role

        Returns:
            Ok(None) if user has the role, Err otherwise
        """
        if not _has_role(user_info.get("roles"), role):
            return Err(InsufficientPermissionsError([role.value]))
        return Ok(None)

    def checkAnyRole(
        self, user_info: UserInfo, roles: list[ManagementRole]
    ) -> Result[None, InsufficientPermissionsError]:
        """
        Check if user has any of the specified roles.

        Args:
            user_info: The authenticated user info
            roles: List of roles (user needs at least one)

        Returns:
            Ok(None) if user has any role, Err otherwise
        """
        if not _has_any_role(user_info.get("roles"), roles):
            role_values = [r.value for r in roles]
            return Err(InsufficientPermissionsError(role_values))
        return Ok(None)

    def checkAllRoles(
        self, user_info: UserInfo, roles: list[ManagementRole]
    ) -> Result[None, InsufficientPermissionsError]:
        """
        Check if user has all of the specified roles.

        Args:
            user_info: The authenticated user info
            roles: List of roles (user needs all)

        Returns:
            Ok(None) if user has all roles, Err otherwise
        """
        if not _has_all_roles(user_info.get("roles"), roles):
            role_values = [r.value for r in roles]
            return Err(InsufficientPermissionsError(role_values))
        return Ok(None)
