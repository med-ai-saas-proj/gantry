"""Keycloak Admin REST API client for Organization operations.

Wraps the relevant Keycloak endpoints that deal with organizations,
members, invitations, and user accounts.
"""

from src.shared.custom_types.error_exception import RecoverableError

from typing import Any

import httpx
from safe_result import Ok, Err, Result


_HTTP_TIMEOUT_SECONDS = 15.0


# Error types
class KeycloakOrgError(RecoverableError):
    """Generic Keycloak organization error."""

    status = 502
    code = "keycloak_org_error"
    title = "Keycloak Organization Error"
    detail = "Failed to perform Keycloak organization operation."


class KeycloakOrgBadRequestError(RecoverableError):
    status = 400
    code = "keycloak_org_bad_request"
    title = "Bad Request"
    detail = "Invalid request sent to Keycloak organization API."


class KeycloakOrgConfigError(KeycloakOrgError):
    """Configuration error for Keycloak organization integration."""

    status = 500
    code = "keycloak_org_misconfigured"
    title = "Keycloak Organization Misconfigured"
    detail = "Service account credentials are not configured."


class KeycloakOrgForbiddenError(RecoverableError):
    status = 403
    code = "keycloak_org_forbidden"
    title = "Forbidden"
    detail = "Permission denied by Keycloak organization API."


class KeycloakOrgConflictError(RecoverableError):
    status = 409
    code = "keycloak_org_conflict"
    title = "Conflict"
    detail = "Keycloak organization request conflicts with current state."


class OrgNotFoundError(RecoverableError):
    status = 404
    code = "org_not_found"
    title = "Organization Not Found"
    detail = "The specified organization does not exist."


class MemberNotFoundError(RecoverableError):
    status = 404
    code = "member_not_found"
    title = "Member Not Found"
    detail = "The specified member does not exist in this organization."


class InvitationNotFoundError(RecoverableError):
    status = 404
    code = "invitation_not_found"
    title = "Invitation Not Found"
    detail = "The specified invitation does not exist."


class IdentityProviderNotFoundError(RecoverableError):
    status = 404
    code = "identity_provider_not_found"
    title = "Identity Provider Not Found"
    detail = "The specified identity provider was not found."


class InviteEmailError(RecoverableError):
    """Keycloak could not send the invitation email."""

    status = 502
    code = "invite_email_failed"
    title = "Invitation Email Failed"
    detail = (
        "The invitation was created but the email"
        " could not be sent. Check SMTP settings."
    )


class UserNotInOrganizationError(RecoverableError):
    status = 403
    code = "user_not_in_organization"
    title = "User Not In Organization"
    detail = "The user is not a member of this organization."


# Client
class KeycloakOrgClient:
    """Async client for Keycloak Organization Admin REST API."""

    def __init__(
        self,
        server_url: str,
        realm: str,
        service_client_id: str,
        service_client_secret: str,
    ):
        self.base_url = server_url.rstrip("/")
        self.realm = realm
        self.service_client_id = service_client_id
        self.service_client_secret = service_client_secret

    # token
    async def _get_service_token(
        self,
    ) -> Result[str, KeycloakOrgError]:
        if not self.service_client_secret:
            return Err(KeycloakOrgConfigError())

        url = (
            f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"
        )
        data = {
            "client_id": self.service_client_id,
            "client_secret": self.service_client_secret,
            "grant_type": "client_credentials",
        }
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.post(
                    url,
                    data=data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                )
                if resp.status_code == 200:
                    token = resp.json().get("access_token")
                    if token:
                        return Ok(token)
                return Err(KeycloakOrgError())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    def _admin_base(self) -> str:
        return f"{self.base_url}/admin/realms/{self.realm}"

    # organisation
    async def get_organizations_count(
        self,
        exact: bool | None = None,
        q: str | None = None,
        search: str | None = None,
    ) -> Result[int, RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        params: dict[str, str] = {}
        if exact is not None:
            params["exact"] = str(exact).lower()
        if q:
            params["q"] = q
        if search:
            params["search"] = search

        url = f"{self._admin_base()}/organizations/count"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.get(
                    url,
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(OrgNotFoundError())
                if resp.status_code != 200:
                    return Err(KeycloakOrgError())
                return Ok(resp.json())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def list_organizations(
        self,
        brief_representation: bool = True,
        exact: bool | None = None,
        first: int | None = None,
        max_results: int | None = None,
        q: str | None = None,
        search: str | None = None,
    ) -> Result[list[dict[str, Any]], RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        params: dict[str, str | int] = {
            "briefRepresentation": str(brief_representation).lower()
        }
        if exact is not None:
            params["exact"] = str(exact).lower()
        if first is not None:
            params["first"] = first
        if max_results is not None:
            params["max"] = max_results
        if q:
            params["q"] = q
        if search:
            params["search"] = search

        url = f"{self._admin_base()}/organizations"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.get(
                    url,
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(OrgNotFoundError())
                if resp.status_code != 200:
                    return Err(KeycloakOrgError())
                return Ok(resp.json())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def create_org(
        self,
        payload: dict[str, Any],
    ) -> Result[dict[str, Any], RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/organizations"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 409:
                    return Err(KeycloakOrgConflictError())
                if resp.status_code not in (200, 201, 204):
                    return Err(KeycloakOrgError())
                content: dict[str, Any] = {}
                if resp.content:
                    content = resp.json()
                location = resp.headers.get("Location")
                if location:
                    content["location"] = location
                return Ok(content)
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def get_org(
        self, org_id: str
    ) -> Result[dict[str, Any], RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/organizations/{org_id}"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(OrgNotFoundError())
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code != 200:
                    return Err(KeycloakOrgError())
                return Ok(resp.json())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def update_org(
        self,
        org_id: str,
        payload: dict[str, Any],
    ) -> Result[bool, RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/organizations/{org_id}"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.put(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(OrgNotFoundError())
                if resp.status_code == 409:
                    return Err(KeycloakOrgConflictError())
                if resp.status_code not in (200, 204):
                    return Err(KeycloakOrgError())
                return Ok(True)
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def delete_org(self, org_id: str) -> Result[bool, RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/organizations/{org_id}"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.delete(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(OrgNotFoundError())
                if resp.status_code == 409:
                    return Err(KeycloakOrgConflictError())
                if resp.status_code not in (200, 204):
                    return Err(KeycloakOrgError())
                return Ok(True)
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    # identity providers
    async def list_org_identity_providers(
        self, org_id: str
    ) -> Result[list[dict[str, Any]], RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/organizations/{org_id}/identity-providers"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(OrgNotFoundError())
                if resp.status_code != 200:
                    return Err(KeycloakOrgError())
                return Ok(resp.json())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def get_org_identity_provider(
        self,
        org_id: str,
        alias: str,
    ) -> Result[dict[str, Any], RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = (
            f"{self._admin_base()}/organizations/{org_id}"
            f"/identity-providers/{alias}"
        )
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(IdentityProviderNotFoundError())
                if resp.status_code != 200:
                    return Err(KeycloakOrgError())
                return Ok(resp.json())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def add_org_identity_provider(
        self,
        org_id: str,
        provider_id_or_alias: str,
    ) -> Result[bool, RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/organizations/{org_id}/identity-providers"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.post(
                    url,
                    content=provider_id_or_alias.strip(),
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "text/plain",
                    },
                )
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 409:
                    return Err(KeycloakOrgConflictError())
                if resp.status_code not in (200, 204):
                    return Err(KeycloakOrgError())
                return Ok(True)
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def remove_org_identity_provider(
        self,
        org_id: str,
        alias: str,
    ) -> Result[bool, RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = (
            f"{self._admin_base()}/organizations/{org_id}"
            f"/identity-providers/{alias}"
        )
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.delete(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(IdentityProviderNotFoundError())
                if resp.status_code not in (200, 204):
                    return Err(KeycloakOrgError())
                return Ok(True)
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    # members
    async def get_org_members(
        self,
        org_id: str,
        first: int = 0,
        max_results: int = 20,
        search: str | None = None,
        exact: bool | None = None,
        membership_type: str | None = None,
    ) -> Result[list[dict[str, Any]], RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/organizations/{org_id}/members"
        params: dict[str, str | int] = {
            "first": first,
            "max": max_results,
        }
        if search:
            params["search"] = search
        if exact is not None:
            params["exact"] = str(exact).lower()
        if membership_type:
            params["membershipType"] = membership_type
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.get(
                    url,
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(OrgNotFoundError())
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code != 200:
                    return Err(KeycloakOrgError())
                return Ok(resp.json())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def get_org_member_count(
        self, org_id: str
    ) -> Result[int, RecoverableError]:
        """GET /organizations/{org-id}/members/count"""
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/organizations/{org_id}/members/count"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(OrgNotFoundError())
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code != 200:
                    return Err(KeycloakOrgError())
                return Ok(resp.json())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def get_member_organizations(
        self,
        user_id: str,
        brief_representation: bool = True,
    ) -> Result[list[dict[str, Any]], RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = (
            f"{self._admin_base()}/organizations/members/"
            f"{user_id}/organizations"
        )
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.get(
                    url,
                    params={
                        "briefRepresentation": str(brief_representation).lower()
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 404:
                    return Err(MemberNotFoundError())
                if resp.status_code != 200:
                    return Err(KeycloakOrgError())
                return Ok(resp.json())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def get_org_member(
        self,
        org_id: str,
        user_id: str,
    ) -> Result[dict[str, Any], RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/organizations/{org_id}/members/{user_id}"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(MemberNotFoundError())
                if resp.status_code != 200:
                    return Err(KeycloakOrgError())
                return Ok(resp.json())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def get_member_organizations_in_org(
        self,
        org_id: str,
        user_id: str,
        brief_representation: bool = True,
    ) -> Result[list[dict[str, Any]], RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = (
            f"{self._admin_base()}/organizations/{org_id}"
            f"/members/{user_id}/organizations"
        )
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.get(
                    url,
                    params={
                        "briefRepresentation": str(brief_representation).lower()
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(MemberNotFoundError())
                if resp.status_code != 200:
                    return Err(KeycloakOrgError())
                return Ok(resp.json())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def add_member(
        self,
        org_id: str,
        user_id: str,
    ) -> Result[bool, RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/organizations/{org_id}/members"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.post(
                    url,
                    json=user_id,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(OrgNotFoundError())
                if resp.status_code == 409:
                    return Err(KeycloakOrgConflictError())
                if resp.status_code not in (200, 201, 204):
                    return Err(KeycloakOrgError())
                return Ok(True)
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def remove_member(
        self, org_id: str, user_id: str
    ) -> Result[bool, RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/organizations/{org_id}/members/{user_id}"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.delete(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(MemberNotFoundError())
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code not in (200, 204):
                    return Err(KeycloakOrgError())
                return Ok(True)
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def delete_user(self, user_id: str) -> Result[bool, RecoverableError]:
        """Delete a Keycloak user account entirely."""
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/users/{user_id}"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.delete(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(MemberNotFoundError())
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code not in (200, 204):
                    return Err(KeycloakOrgError())
                return Ok(True)
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def find_user_by_email(
        self,
        email: str,
        exact: bool = True,
    ) -> Result[dict[str, Any] | None, RecoverableError]:
        """Find a Keycloak user by email in the current realm."""
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/users"
        params: dict[str, str] = {
            "email": email,
            "exact": str(exact).lower(),
            "max": "1",
        }
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.get(
                    url,
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code != 200:
                    return Err(KeycloakOrgError())
                users = resp.json()
                if not users:
                    return Ok(None)
                return Ok(users[0])
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    # invitations
    async def invite_user(
        self,
        org_id: str,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> Result[bool, RecoverableError]:
        """POST /organizations/{org-id}/members/invite-user

        Sends an invitation link to existing users or a
        registration link to new users.
        """
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/organizations/{org_id}/members/invite-user"
        form: dict[str, str] = {"email": email}
        if first_name:
            form["firstName"] = first_name
        if last_name:
            form["lastName"] = last_name
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.post(
                    url,
                    data=form,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                if resp.status_code in (200, 204):
                    return Ok(True)
                if resp.status_code == 409:
                    return Ok(True)  # already invited
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(OrgNotFoundError())
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 500:
                    # SMTP not configured – treat as
                    # soft success (invite recorded).
                    return Ok(True)
                return Err(KeycloakOrgError())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def invite_existing_user(
        self,
        org_id: str,
        user_id_or_email: str,
    ) -> Result[bool, RecoverableError]:
        """POST /organizations/{org-id}/members/invite-existing-user"""
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = (
            f"{self._admin_base()}"
            f"/organizations/{org_id}"
            "/members/invite-existing-user"
        )
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.post(
                    url,
                    data={"id": user_id_or_email.strip()},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                if resp.status_code in (200, 201, 204):
                    return Ok(True)
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(OrgNotFoundError())
                if resp.status_code == 409:
                    return Err(KeycloakOrgConflictError())
                if resp.status_code == 500:
                    return Err(KeycloakOrgError())
                return Err(KeycloakOrgError())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def get_invitations(
        self,
        org_id: str,
        email: str | None = None,
        first: int | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        max_results: int | None = None,
        search: str | None = None,
        status: str | None = None,
    ) -> Result[list[dict[str, Any]], RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/organizations/{org_id}/invitations"
        params: dict[str, str | int] = {}
        if email:
            params["email"] = email
        if first is not None:
            params["first"] = first
        if first_name:
            params["firstName"] = first_name
        if last_name:
            params["lastName"] = last_name
        if max_results is not None:
            params["max"] = max_results
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.get(
                    url,
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(OrgNotFoundError())
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code != 200:
                    return Err(KeycloakOrgError())
                return Ok(resp.json())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def get_invitation(
        self, org_id: str, invitation_id: str
    ) -> Result[dict[str, Any], RecoverableError]:
        """GET /organizations/{org-id}/invitations/{id}"""
        token_res = await self._get_service_token()
        if token_res.is_err():
            return Err(KeycloakOrgError())
        token = token_res.unwrap()

        url = (
            f"{self._admin_base()}"
            f"/organizations/{org_id}"
            f"/invitations/{invitation_id}"
        )
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(InvitationNotFoundError())
                if resp.status_code == 405:
                    return Err(InvitationNotFoundError())
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code != 200:
                    return Err(KeycloakOrgError())
                return Ok(resp.json())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def delete_invitation(
        self, org_id: str, invitation_id: str
    ) -> Result[bool, RecoverableError]:
        token_res = await self._get_service_token()
        if token_res.is_err():
            return Err(KeycloakOrgError())
        token = token_res.unwrap()

        url = (
            f"{self._admin_base()}/organizations/{org_id}"
            f"/invitations/{invitation_id}"
        )
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.delete(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(InvitationNotFoundError())
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code not in (200, 204):
                    return Err(KeycloakOrgError())
                return Ok(True)
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def resend_invitation(
        self, org_id: str, invitation_id: str
    ) -> Result[bool, RecoverableError]:
        """POST /organizations/{org-id}/invitations/{id}/resend"""
        token_res = await self._get_service_token()
        if token_res.is_err():
            return Err(KeycloakOrgError())
        token = token_res.unwrap()

        url = (
            f"{self._admin_base()}"
            f"/organizations/{org_id}"
            f"/invitations/{invitation_id}/resend"
        )
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code in (200, 204):
                    return Ok(True)
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(InvitationNotFoundError())
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                return Err(KeycloakOrgError())
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    # user attributes (org permissions)
    async def get_user_attributes(
        self, user_id: str
    ) -> Result[dict[str, Any], RecoverableError]:
        """Get a Keycloak user's attributes."""
        token_res = await self._get_service_token()
        if token_res.is_err():
            return Err(KeycloakOrgError())
        token = token_res.unwrap()

        url = f"{self._admin_base()}/users/{user_id}"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if resp.status_code == 404:
                    return Err(MemberNotFoundError())
                if resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if resp.status_code != 200:
                    return Err(KeycloakOrgError())
                return Ok(resp.json().get("attributes", {}))
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))

    async def set_user_attribute(
        self,
        user_id: str,
        key: str,
        values: list[str],
    ) -> Result[bool, RecoverableError]:
        """Set a single attribute on a Keycloak user.

        We first fetch user, merge the attribute, then PUT the full
        representation back – this is the only safe way in Keycloak.
        """
        token_res = await self._get_service_token()
        if token_res.is_err():
            return token_res
        token = token_res.unwrap()

        url = f"{self._admin_base()}/users/{user_id}"
        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT_SECONDS
            ) as client:
                # Fetch current representation
                get_resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if get_resp.status_code == 403:
                    return Err(KeycloakOrgForbiddenError())
                if get_resp.status_code == 404:
                    return Err(MemberNotFoundError())
                if get_resp.status_code == 400:
                    return Err(KeycloakOrgBadRequestError())
                if get_resp.status_code != 200:
                    return Err(KeycloakOrgError())

                user_rep = get_resp.json()
                attrs = user_rep.get("attributes", {})
                attrs[key] = values
                user_rep["attributes"] = attrs

                # PUT back
                put_resp = await client.put(
                    url,
                    json=user_rep,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )
                if put_resp.status_code not in (200, 204):
                    if put_resp.status_code == 400:
                        return Err(KeycloakOrgBadRequestError())
                    if put_resp.status_code == 403:
                        return Err(KeycloakOrgForbiddenError())
                    return Err(KeycloakOrgError())
                return Ok(True)
        except Exception as e:
            return Err(KeycloakOrgError(from_exception=e))
