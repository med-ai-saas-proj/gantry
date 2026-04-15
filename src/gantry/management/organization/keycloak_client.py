"""Keycloak Admin client adapter for Organization operations.

This module uses `python-keycloak` for authentication/session handling,
while organization endpoints are called via raw admin REST paths.
"""

from gantry.shared.custom_types.error_exception import RecoverableError

import json
from typing import Any
from urllib.parse import urljoin

from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
from pyrusult import Ok, Err, Result, ResultStatus
from keycloak.exceptions import KeycloakError


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


type KeycloakPossibleError = (
    KeycloakOrgBadRequestError
    | KeycloakOrgForbiddenError
    | KeycloakOrgConflictError
    | KeycloakOrgConfigError
    | KeycloakOrgError
)


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


class KeycloakOrgClient:
    """Async adapter over python-keycloak admin connection."""

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

        if not self.service_client_secret:
            self._connection = None
            self._admin = None
            self._init_error: KeycloakOrgError | None = KeycloakOrgConfigError()
            return

        try:
            conn = KeycloakOpenIDConnection(
                server_url=self.base_url,
                realm_name=self.realm,
                grant_type="client_credentials",
                client_id=self.service_client_id,
                client_secret_key=self.service_client_secret,
                verify=True,
            )
            self._connection = conn
            self._admin = KeycloakAdmin(connection=conn)
            self._init_error = None
        except Exception as exc:
            self._connection = None
            self._admin = None
            self._init_error = KeycloakOrgError(from_exception=exc)

    def _adminBase(self) -> str:
        return f"/admin/realms/{self.realm}"

    def _parseResponseJson(self, response: Any) -> Any:
        if not getattr(response, "content", b""):
            return None
        try:
            return response.json()
        except Exception:
            return None

    async def _rawRequest(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> Result[Any, KeycloakOrgError]:
        if self._init_error is not None:
            return Err(self._init_error)
        if self._connection is None:
            return Err(KeycloakOrgError())

        try:
            if headers is not None:
                await self._connection.a__refresh_if_required()
                request_headers = {**self._connection.headers, **headers}
                request_kwargs: dict[str, Any] = {
                    "headers": request_headers,
                    "timeout": self._connection.timeout,
                }
                if params is not None:
                    request_kwargs["params"] = params
                if data is not None:
                    if isinstance(data, str):
                        request_kwargs["content"] = data
                    else:
                        request_kwargs["data"] = data

                response = await self._connection.async_s.request(
                    method=method.upper(),
                    url=urljoin(self.base_url, path),
                    **request_kwargs,
                )
                if response.status_code == 401:
                    await self._connection.a_refresh_token()
                    request_kwargs["headers"] = {
                        **self._connection.headers,
                        **headers,
                    }
                    response = await self._connection.async_s.request(
                        method=method.upper(),
                        url=urljoin(self.base_url, path),
                        **request_kwargs,
                    )
                return Ok(response)

            match method:
                case "get":
                    response = await self._connection.a_raw_get(
                        path, params=params, headers=headers
                    )
                case "delete":
                    response = await self._connection.a_raw_delete(
                        path, params=params, headers=headers
                    )
                case "post":
                    response = await self._connection.a_raw_post(
                        path, params=params, data=data, headers=headers
                    )
                case "put":
                    response = await self._connection.a_raw_put(
                        path, params=params, data=data, headers=headers
                    )
                case _:
                    return Err(KeycloakOrgError())
            return Ok(response)
        except KeycloakError as exc:
            return Err(KeycloakOrgError(from_exception=exc))
        except Exception as exc:
            return Err(KeycloakOrgError(from_exception=exc))

    def _mapStatusError[T, U](
        self,
        status_code: int,
        *,
        not_found_error: T | None = None,
        extra_error_map: dict[int, U] | None = None,
        include_conflict: bool = True,
    ) -> T | U | KeycloakPossibleError:
        if extra_error_map is not None and status_code in extra_error_map:
            return extra_error_map[status_code]
        if status_code == 400:
            return KeycloakOrgBadRequestError()
        if status_code == 403:
            return KeycloakOrgForbiddenError()
        if status_code == 404 and not_found_error is not None:
            return not_found_error
        if status_code == 409 and include_conflict:
            return KeycloakOrgConflictError()
        return KeycloakOrgError()

    def _mapKeycloakError[T, U](
        self,
        exc: KeycloakError,
        *,
        not_found_error: T | None = None,
        extra_error_map: dict[int, U] | None = None,
        include_conflict: bool = True,
    ) -> KeycloakPossibleError | T | U:
        response_code = getattr(exc, "response_code", None)
        if isinstance(response_code, int):
            return self._mapStatusError(
                response_code,
                not_found_error=not_found_error,
                extra_error_map=extra_error_map,
                include_conflict=include_conflict,
            )
        return KeycloakOrgError(from_exception=exc)

    async def getOrg(
        self, org_id: str
    ) -> Result[dict[str, Any], OrgNotFoundError | KeycloakOrgError]:
        if self._init_error is not None:
            return Err(self._init_error)
        if self._admin is None:
            return Err(KeycloakOrgError())

        try:
            payload = await self._admin.a_get_organization(org_id)
            if isinstance(payload, dict):
                return Ok(payload)
            return Err(KeycloakOrgError())
        except KeycloakError as exc:
            return Err(
                self._mapKeycloakError(
                    exc,
                    not_found_error=OrgNotFoundError(),
                )
            )
        except Exception as exc:
            return Err(KeycloakOrgError(from_exception=exc))

    async def updateOrg(
        self,
        org_id: str,
        payload: dict[str, Any],
    ) -> Result[bool, OrgNotFoundError | KeycloakOrgError]:
        if self._init_error is not None:
            return Err(self._init_error)
        if self._admin is None:
            return Err(KeycloakOrgError())

        try:
            await self._admin.a_update_organization(org_id, payload)
            return Ok(True)
        except KeycloakError as exc:
            return Err(
                self._mapKeycloakError(
                    exc,
                    not_found_error=OrgNotFoundError(),
                )
            )
        except Exception as exc:
            return Err(KeycloakOrgError(from_exception=exc))

    async def deleteOrg(
        self, org_id: str
    ) -> Result[bool, OrgNotFoundError | KeycloakOrgError]:
        if self._init_error is not None:
            return Err(self._init_error)
        if self._admin is None:
            return Err(KeycloakOrgError())

        try:
            await self._admin.a_delete_organization(org_id)
            return Ok(True)
        except KeycloakError as exc:
            return Err(
                self._mapKeycloakError(
                    exc,
                    not_found_error=OrgNotFoundError(),
                )
            )
        except Exception as exc:
            return Err(KeycloakOrgError(from_exception=exc))

    async def getOrgMembers(
        self,
        org_id: str,
        first: int = 0,
        max_results: int = 20,
        search: str | None = None,
        exact: bool | None = None,
        membership_type: str | None = None,
    ) -> Result[list[dict[str, Any]], OrgNotFoundError | KeycloakOrgError]:
        query: dict[str, Any] = {"first": first, "max": max_results}
        if search:
            query["search"] = search
        if exact is not None:
            query["exact"] = str(exact).lower()
        if membership_type:
            query["membershipType"] = membership_type

        if self._init_error is not None:
            return Err(self._init_error)
        if self._admin is None:
            return Err(KeycloakOrgError())

        try:
            payload = await self._admin.a_get_organization_members(
                org_id, query=query
            )
            if isinstance(payload, list):
                return Ok(payload)
            return Err(KeycloakOrgError())
        except KeycloakError as exc:
            return Err(
                self._mapKeycloakError(
                    exc,
                    not_found_error=OrgNotFoundError(),
                )
            )
        except Exception as exc:
            return Err(KeycloakOrgError(from_exception=exc))

    async def getOrgMemberCount(
        self, org_id: str
    ) -> Result[int, OrgNotFoundError | KeycloakOrgError]:
        if self._init_error is not None:
            return Err(self._init_error)
        if self._admin is None:
            return Err(KeycloakOrgError())

        try:
            payload = await self._admin.a_get_organization_members_count(org_id)
            if isinstance(payload, int):
                return Ok(payload)
            return Err(KeycloakOrgError())
        except KeycloakError as exc:
            return Err(
                self._mapKeycloakError(
                    exc,
                    not_found_error=OrgNotFoundError(),
                )
            )
        except Exception as exc:
            return Err(KeycloakOrgError(from_exception=exc))

    async def getMemberOrganizations(
        self,
        user_id: str,
        brief_representation: bool = True,
    ) -> Result[list[dict[str, Any]], MemberNotFoundError | KeycloakOrgError]:
        del brief_representation
        if self._init_error is not None:
            return Err(self._init_error)
        if self._admin is None:
            return Err(KeycloakOrgError())

        try:
            payload = await self._admin.a_get_user_organizations(user_id)
            if isinstance(payload, list):
                return Ok(payload)
            return Err(KeycloakOrgError())
        except KeycloakError as exc:
            return Err(
                self._mapKeycloakError(
                    exc,
                    not_found_error=MemberNotFoundError(),
                )
            )
        except Exception as exc:
            return Err(KeycloakOrgError(from_exception=exc))

    async def removeMember(
        self, org_id: str, user_id: str
    ) -> Result[bool, MemberNotFoundError | KeycloakOrgError]:
        if self._init_error is not None:
            return Err(self._init_error)
        if self._admin is None:
            return Err(KeycloakOrgError())

        try:
            await self._admin.a_organization_user_remove(user_id, org_id)
            return Ok(True)
        except KeycloakError as exc:
            return Err(
                self._mapKeycloakError(
                    exc,
                    not_found_error=MemberNotFoundError(),
                )
            )
        except Exception as exc:
            return Err(KeycloakOrgError(from_exception=exc))

    async def deleteUser(
        self, user_id: str
    ) -> Result[bool, MemberNotFoundError | KeycloakOrgError]:
        if self._init_error is not None:
            return Err(self._init_error)
        if self._admin is None:
            return Err(KeycloakOrgError())

        try:
            await self._admin.a_delete_user(user_id)
            return Ok(True)
        except KeycloakError as exc:
            return Err(
                self._mapKeycloakError(
                    exc,
                    not_found_error=MemberNotFoundError(),
                )
            )
        except Exception as exc:
            return Err(KeycloakOrgError(from_exception=exc))

    async def findUserByEmail(
        self,
        email: str,
        exact: bool = True,
    ) -> Result[
        dict[str, Any] | None,
        KeycloakOrgBadRequestError
        | KeycloakOrgForbiddenError
        | KeycloakOrgError,
    ]:
        if self._init_error is not None:
            return Err(self._init_error)
        if self._admin is None:
            return Err(KeycloakOrgError())

        try:
            payload = await self._admin.a_get_users(
                query={
                    "email": email,
                    "exact": str(exact).lower(),
                    "max": 1,
                }
            )
            if not isinstance(payload, list):
                return Err(KeycloakOrgError())
            if not payload:
                return Ok(None)
            first = payload[0]
            if not isinstance(first, dict):
                return Err(KeycloakOrgError())
            return Ok(first)
        except KeycloakError as exc:
            return Err(
                self._mapKeycloakError(
                    exc,
                    include_conflict=False,
                )
            )
        except Exception as exc:
            return Err(KeycloakOrgError(from_exception=exc))

    async def inviteUser(
        self,
        org_id: str,
        email: str,
        client_id: str | None = None,
        redirect_uri: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> Result[bool, KeycloakPossibleError | OrgNotFoundError]:
        path = f"{self._adminBase()}/organizations/{org_id}/members/invite-user"
        form: dict[str, str] = {"email": email}
        if client_id:
            form["clientId"] = client_id
        if redirect_uri:
            form["redirectUri"] = redirect_uri
        if first_name:
            form["firstName"] = first_name
        if last_name:
            form["lastName"] = last_name

        response_res = await self._rawRequest(
            "post",
            path,
            data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response_res.status == ResultStatus.Err:
            return response_res

        response = response_res.unwrap()
        if response.status_code in (200, 204):
            return Ok(True)
        if response.status_code == 409:
            return Ok(True)
        if response.status_code == 500:
            # Treat SMTP issue as soft success.
            return Ok(True)

        return Err(
            self._mapStatusError(
                response.status_code,
                not_found_error=OrgNotFoundError(),
            )
        )

    async def getInvitations(
        self,
        org_id: str,
        email: str | None = None,
        first: int | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        max_results: int | None = None,
        search: str | None = None,
        status: str | None = None,
    ) -> Result[
        list[dict[str, Any]],
        OrgNotFoundError
        | KeycloakOrgBadRequestError
        | KeycloakOrgForbiddenError
        | KeycloakOrgConflictError
        | KeycloakOrgError,
    ]:
        path = f"{self._adminBase()}/organizations/{org_id}/invitations"
        query: dict[str, Any] = {}
        if email:
            query["email"] = email
        if first is not None:
            query["first"] = first
        if first_name:
            query["firstName"] = first_name
        if last_name:
            query["lastName"] = last_name
        if max_results is not None:
            query["max"] = max_results
        if search:
            query["search"] = search
        if status:
            query["status"] = status

        response_res = await self._rawRequest("get", path, params=query)
        if response_res.status == ResultStatus.Err:
            return response_res

        response = response_res.unwrap()
        if response.status_code != 200:
            return Err(
                self._mapStatusError(
                    response.status_code,
                    not_found_error=OrgNotFoundError(),
                )
            )

        payload = self._parseResponseJson(response)
        if isinstance(payload, list):
            return Ok(payload)
        return Err(KeycloakOrgError())

    async def getInvitation(
        self, org_id: str, invitation_id: str
    ) -> Result[
        dict[str, Any], KeycloakPossibleError | InvitationNotFoundError
    ]:
        path = f"{self._adminBase()}/organizations/{org_id}/invitations/{invitation_id}"
        response_res = await self._rawRequest("get", path)
        if response_res.status == ResultStatus.Err:
            # return Err(KeycloakOrgError())
            return response_res

        response = response_res.unwrap()
        if response.status_code != 200:
            return Err(
                self._mapStatusError(
                    response.status_code,
                    not_found_error=InvitationNotFoundError(),
                    extra_error_map={405: InvitationNotFoundError()},
                    include_conflict=False,
                )
            )

        payload = self._parseResponseJson(response)
        if isinstance(payload, dict):
            return Ok(payload)
        return Err(KeycloakOrgError())

    async def deleteInvitation(
        self, org_id: str, invitation_id: str
    ) -> Result[
        bool,
        KeycloakPossibleError | InvitationNotFoundError,
    ]:
        path = f"{self._adminBase()}/organizations/{org_id}/invitations/{invitation_id}"
        response_res = await self._rawRequest("delete", path)
        if response_res.status == ResultStatus.Err:
            return response_res

        response = response_res.unwrap()
        if response.status_code in (200, 204):
            return Ok(True)
        return Err(
            self._mapStatusError(
                response.status_code,
                not_found_error=InvitationNotFoundError(),
                include_conflict=False,
            )
        )

    async def resendInvitation(
        self, org_id: str, invitation_id: str
    ) -> Result[
        bool,
        InvitationNotFoundError
        | KeycloakOrgBadRequestError
        | KeycloakOrgForbiddenError
        | KeycloakOrgError,
    ]:
        path = (
            f"{self._adminBase()}/organizations/{org_id}"
            f"/invitations/{invitation_id}/resend"
        )
        response_res = await self._rawRequest("post", path)
        if response_res.status == ResultStatus.Err:
            return response_res

        response = response_res.unwrap()
        if response.status_code in (200, 204):
            return Ok(True)
        return Err(
            self._mapStatusError(
                response.status_code,
                not_found_error=InvitationNotFoundError(),
                include_conflict=False,
            )
        )

    async def getUserAttributes(
        self, user_id: str
    ) -> Result[dict[str, Any], MemberNotFoundError | KeycloakOrgError]:
        if self._init_error is not None:
            return Err(self._init_error)
        if self._admin is None:
            return Err(KeycloakOrgError())

        try:
            user = await self._admin.a_get_user(user_id)
            attrs = user.get("attributes", {})
            if isinstance(attrs, dict):
                return Ok(attrs)
            return Ok({})
        except KeycloakError as exc:
            return Err(
                self._mapKeycloakError(
                    exc,
                    not_found_error=MemberNotFoundError(),
                    include_conflict=False,
                )
            )
        except Exception as exc:
            return Err(KeycloakOrgError(from_exception=exc))

    async def setUserAttribute(
        self,
        user_id: str,
        key: str,
        values: list[str],
    ) -> Result[bool, MemberNotFoundError | KeycloakOrgError]:
        if self._init_error is not None:
            return Err(self._init_error)
        if self._admin is None:
            return Err(KeycloakOrgError())

        try:
            user = await self._admin.a_get_user(user_id)
            attrs = user.get("attributes", {})
            if not isinstance(attrs, dict):
                attrs = {}
            attrs[key] = values
            user["attributes"] = attrs
            await self._admin.a_update_user(user_id, user)
            return Ok(True)
        except KeycloakError as exc:
            return Err(
                self._mapKeycloakError(
                    exc,
                    not_found_error=MemberNotFoundError(),
                    include_conflict=False,
                )
            )
        except Exception as exc:
            return Err(KeycloakOrgError(from_exception=exc))
