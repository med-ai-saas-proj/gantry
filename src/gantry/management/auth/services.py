"""Authentication and authorization services for management API."""

from gantry.shared.consts import messages_const
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

    def __init__(self, server_url: str, realm: str, client_id: str):
        # Strip trailing slash from server URL
        self.server_url = server_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id

        self.jwks_url = (
            f"{self.server_url}/realms/{self.realm}"
            f"/protocol/openid-connect/certs"
        )
        self.issuer = f"{self.server_url}/realms/{self.realm}"

        self.jwk_client = PyJWKClient(self.jwks_url, cache_keys=True)

    def verifyToken(self, token: str) -> Result[UserInfo, UnauthorizedError]:
        """Verify Keycloak JWT token."""
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

            return self._mapClaimsToAuthInfo(payload)

        except Exception as e:
            return Err(UnauthorizedError(from_exception=e))

    def _mapClaimsToAuthInfo(
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
        if not org_id:
            return Err(MissingOrganizationClaimError())

        auth_info: UserInfo = {
            "id": claims["sub"],
            "username": username if isinstance(username, str) else None,
            "email": claims.get("email"),
            "roles": roles,
            "org_id": org_id,
        }
        project_ids = self._extractProjectIds(claims, roles)
        if project_ids:
            auth_info["project_ids"] = project_ids

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
        """Extract distinct project ids from flat token entries like `proj:perm`."""
        project_ids: list[str] = []
        seen: set[str] = set()
        for entry in entries:
            if not isinstance(entry, str):
                continue
            project_id, separator, permission = entry.partition(":")
            if not separator or not project_id or not permission:
                continue
            if project_id in seen:
                continue
            seen.add(project_id)
            project_ids.append(project_id)
        return project_ids

    def _extractProjectIds(
        self,
        claims: dict[str, Any],
        roles: list[str],
    ) -> list[str]:
        """Extract project ids directly from token-carried project permission entries."""
        raw = claims.get("project_permissions", [])
        if isinstance(raw, str):
            project_entries = [raw]
        elif isinstance(raw, list):
            project_entries = [
                entry for entry in raw if isinstance(entry, str)
            ]
        else:
            project_entries = []

        # Some environments flatten these entries into the role list instead of
        # emitting a dedicated `project_permissions` claim.
        return self._extractProjectIdsFromEntries(project_entries or roles)

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
