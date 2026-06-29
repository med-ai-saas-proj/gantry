"""Business-logic service for Organization operations.

Orchestrates the Keycloak admin client and Postgres repositories.
"""

from pyrusult import Ok, Err, Result, ResultStatus
from gantry.db import AsyncSessionManager
from gantry.keycloak import (
    KeycloakOrgError,
    OrgNotFoundError,
    MemberNotFoundError,
    KeycloakServiceClient,
    InvitationNotFoundError,
    UserNotInOrganizationError,
)
from gantry.keycloak.services import KeycloakPossibleError
from gantry.shared.utils.scaled_amount import int_to_scaled_int
from gantry.shared.custom_types.error_exception import RecoverableError

from .dtos import (
    OrgInfoResponse,
    OrgListResponse,
    OrgUserResponse,
    InvitationResponse,
    OrgSettingsResponse,
    OrgUserListResponse,
    DeleteRequestResponse,
    InvitationListResponse,
    UserPermissionsResponse,
)
from .entities import (
    CreateOrgPayload,
    KeycloakOrgPayload,
    KeycloakUserPayload,
    UserAttributePayload,
    KeycloakInvitationPayload,
)
from .settings import getOrgSettings
from .permissions import OrgPermission, has_permission
from .repositories import (
    OrgSettingsRepository,
    OrgDeletionRequestRepository,
)

from typing import Any, cast
from datetime import UTC, datetime, timedelta

from structlog.stdlib import BoundLogger

_ORG_PERM_ATTR = "org_permissions"


class DeletionAlreadyRequestedError(RecoverableError):
    status = 409
    code = "deletion_already_requested"
    title = "Deletion Already Requested"
    detail = "A deletion request for this organization already exists."


class DeletionRequestNotFoundError(RecoverableError):
    status = 404
    code = "deletion_request_not_found"
    title = "Deletion Request Not Found"
    detail = "No pending deletion request exists for this organization."


class InvalidPermissionError(RecoverableError):
    status = 400
    code = "invalid_org_permission"
    title = "Invalid Organization Permission"
    detail = "One or more permissions are invalid."


class ReadOwnPermissionsOrManageRequiredError(RecoverableError):
    status = 403
    code = "insufficient_org_permission"
    title = "Insufficient Organization Permission"
    detail = (
        "You can read only your own permissions unless you have "
        "organization.users.permissions.read_write."
    )


class OwnerRequiredForGrantError(RecoverableError):
    status = 403
    code = "owner_required_for_permission_grant"
    title = "Owner Required"
    detail = (
        "Only organization owner can grant "
        "organization.users.permissions.read_write."
    )


class OwnerPermissionRequiredError(RecoverableError):
    status = 403
    code = "owner_required"
    title = "Owner Required"
    detail = "Only organization owner can perform this operation."


class OwnerPermissionImmutableError(RecoverableError):
    status = 403
    code = "owner_permission_immutable"
    title = "Owner Permission Immutable"
    detail = "Organization owner permission is permanent and cannot be removed."


class OwnerTransferNotAllowedError(RecoverableError):
    status = 403
    code = "owner_transfer_not_allowed"
    title = "Owner Transfer Not Allowed"
    detail = "Organization owner cannot be transferred to another user."


class OwnerRemovalNotAllowedError(RecoverableError):
    status = 403
    code = "owner_removal_not_allowed"
    title = "Owner Removal Not Allowed"
    detail = "Organization owner cannot be removed from the organization."


class OwnerNotFoundError(RecoverableError):
    status = 409
    code = "owner_not_found"
    title = "Owner Not Found"
    detail = "No organization owner is configured for this organization."


class MultipleOwnersError(RecoverableError):
    status = 409
    code = "multiple_owners_not_allowed"
    title = "Multiple Owners Not Allowed"
    detail = "An organization must have exactly one owner."


class UserAlreadyInOrganizationError(RecoverableError):
    status = 409
    code = "user_already_in_organization"
    title = "User Already In Organization"
    detail = "The user is already a member of this organization."


class UserAlreadyInAnotherOrganizationError(RecoverableError):
    status = 409
    code = "user_already_in_another_organization"
    title = "User Already In Another Organization"
    detail = "A user can belong to only one organization."


class MultipleOrganizationMembershipError(RecoverableError):
    status = 409
    code = "multiple_org_membership_not_allowed"
    title = "Multiple Organization Membership Not Allowed"
    detail = "A user can belong to only one organization."


def _extract_org_ids(orgs: list[KeycloakOrgPayload]) -> set[str]:
    """Collect non-empty organization ids from Keycloak org payloads."""
    return {str(org.get("id", "")) for org in orgs if org.get("id")}


def _matches_org_query(org: KeycloakOrgPayload, q: str | None) -> bool:
    """Return true when an organization matches a user-supplied search term."""
    if not q:
        return True
    query = q.casefold()
    fields = (
        org.get("id"),
        org.get("name"),
        org.get("alias"),
    )
    return any(
        query in str(value).casefold() for value in fields if value is not None
    )


class OrgService:
    """Coordinate organization business rules across Keycloak and storage."""

    def __init__(
        self,
        kc_client: KeycloakServiceClient,
        settings_repo: OrgSettingsRepository,
        deletion_repo: OrgDeletionRequestRepository,
        session_manager: AsyncSessionManager,
        logger: BoundLogger,
    ):
        self.kc = kc_client
        self.settings_repo = settings_repo
        self.deletion_repo = deletion_repo
        self.session_manager = session_manager
        self.logger = logger

    def _computeCancelBefore(self, requested_at: datetime) -> datetime:
        """Compute the deletion cancellation deadline from settings."""
        days = getOrgSettings().deletion_cancel_window_days
        return requested_at + timedelta(days=days)

    async def _ensureOrgExists(
        self, org_id: str
    ) -> Result[KeycloakOrgPayload, OrgNotFoundError | KeycloakOrgError]:
        """Fetch the organization from Keycloak or return the upstream error."""
        return cast(
            Result[KeycloakOrgPayload, OrgNotFoundError | KeycloakOrgError],
            await self.kc.getOrg(org_id),
        )

    async def _ensureUserInOrg(
        self, org_id: str, user_id: str
    ) -> Result[
        bool,
        MemberNotFoundError
        | KeycloakOrgError
        | MultipleOrganizationMembershipError
        | UserNotInOrganizationError,
    ]:
        """Verify the user belongs to exactly this organization."""
        orgs_res = await self.kc.getMemberOrganizations(user_id)
        if orgs_res.status == ResultStatus.Err:
            return orgs_res.into()

        orgs = cast(list[KeycloakOrgPayload], orgs_res.unwrap())
        unique_org_ids = {
            str(org.get("id", "")) for org in orgs if org.get("id")
        }
        if len(unique_org_ids) > 1:
            return Err(MultipleOrganizationMembershipError())
        for org in orgs:
            if org.get("id") == org_id:
                return Ok(True)
        return Err(UserNotInOrganizationError())

    def _extractUserPermissions(self, attrs: UserAttributePayload) -> list[str]:
        """Normalize organization permissions from Keycloak user attributes."""
        # Keycloak user-profile validation allows org_permissions.
        legacy = attrs.get(_ORG_PERM_ATTR, [])
        if isinstance(legacy, str):
            legacy = [legacy]
        if isinstance(legacy, list):
            return [p for p in legacy if isinstance(p, str)]
        return []

    def _flattenSettings(
        self,
        data: dict[str, Any],
        prefix: str = "",
    ) -> dict[str, Any]:
        """Flatten nested settings dictionaries into dot-notation keys."""
        flattened: dict[str, Any] = {}
        for key, value in data.items():
            final_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                flattened.update(self._flattenSettings(value, prefix=final_key))
            else:
                flattened[final_key] = value
        return flattened

    async def _getMemberPermissions(
        self, org_id: str, user_id: str
    ) -> Result[
        list[str],
        MemberNotFoundError
        | KeycloakOrgError
        | MultipleOrganizationMembershipError
        | UserNotInOrganizationError,
    ]:
        """Load organization permissions for a confirmed organization member."""
        member_res = await self._ensureUserInOrg(org_id, user_id)
        if member_res.status == ResultStatus.Err:
            return member_res.into()

        attrs_res = await self.kc.getUserAttributes(user_id)
        if attrs_res.status == ResultStatus.Err:
            return attrs_res.into()
        attrs = attrs_res.unwrap()
        return Ok(self._extractUserPermissions(attrs))

    async def _getOrgOwnerId(
        self, org_id: str
    ) -> Result[
        str,
        OrgNotFoundError
        | MemberNotFoundError
        | KeycloakOrgError
        | OwnerNotFoundError
        | MultipleOwnersError,
    ]:
        """Find the single configured organization owner from org members."""
        first = 0
        max_results = 100
        owners: list[str] = []

        while True:
            members_res = await self.kc.getOrgMembers(
                org_id, first=first, max_results=max_results
            )
            if members_res.status == ResultStatus.Err:
                return members_res.into()
            members = cast(list[KeycloakUserPayload], members_res.unwrap())
            if not members:
                break

            for member in members:
                member_id = member.get("id")
                if not member_id:
                    continue
                attrs_res = await self.kc.getUserAttributes(member_id)
                if attrs_res.status == ResultStatus.Err:
                    return attrs_res.into()
                perms = self._extractUserPermissions(attrs_res.unwrap())
                if OrgPermission.OWNER.value in perms:
                    owners.append(member_id)

            if len(members) < max_results:
                break
            first += max_results

        unique_owners = list(dict.fromkeys(owners))
        if not unique_owners:
            return Err(OwnerNotFoundError())
        if len(unique_owners) > 1:
            return Err(MultipleOwnersError())
        return Ok(unique_owners[0])

    async def _syncMetadataFromKeycloak(
        self, org_id: str
    ) -> Result[
        OrgInfoResponse,
        OrgNotFoundError
        | MemberNotFoundError
        | KeycloakOrgError
        | OwnerNotFoundError
        | MultipleOwnersError,
    ]:
        """Build organization metadata from Keycloak plus owner resolution."""
        org_res = await self.kc.getOrg(org_id)
        if org_res.status == ResultStatus.Err:
            return org_res.into()
        org = cast(KeycloakOrgPayload, org_res.unwrap())
        name = str(org.get("name") or org_id)

        owner_id_res = await self._getOrgOwnerId(org_id)
        if owner_id_res.status == ResultStatus.Err:
            if isinstance(owner_id_res.err(), OwnerNotFoundError):
                return Ok(
                    OrgInfoResponse(
                        org_id=str(org.get("id") or org_id),
                        name=name,
                        owner_id=None,
                    )
                )
            return owner_id_res.into()
        return Ok(
            OrgInfoResponse(
                org_id=str(org.get("id") or org_id),
                name=name,
                owner_id=owner_id_res.unwrap(),
            )
        )

    # delete org
    async def requestDeleteOrg(
        self, org_id: str
    ) -> Result[
        DeleteRequestResponse,
        OrgNotFoundError | KeycloakOrgError | DeletionAlreadyRequestedError,
    ]:
        """Create a delayed deletion request for an existing organization."""
        org_res = await self._ensureOrgExists(org_id)
        if org_res.status == ResultStatus.Err:
            return org_res.into()

        async with self.session_manager.get_session() as session:
            existing = await self.deletion_repo.getByOrgId(session, org_id)
            if existing is not None:
                return Err(DeletionAlreadyRequestedError())

            record = await self.deletion_repo.upsertRequest(
                session=session,
                org_id=org_id,
            )
            requested_at_dt = record.requested_at
            cancel_before_dt = self._computeCancelBefore(requested_at_dt)
            await session.commit()

            return Ok(
                DeleteRequestResponse(
                    id=org_id,
                    requested_at=requested_at_dt.isoformat(),
                    cancel_before=cancel_before_dt.isoformat(),
                )
            )

    async def cancelDeleteOrg(
        self, org_id: str
    ) -> Result[bool, DeletionRequestNotFoundError]:
        """Cancel a pending organization deletion request."""
        async with self.session_manager.get_session() as session:
            deleted = await self.deletion_repo.deleteByOrgId(session, org_id)
            if not deleted:
                return Err(DeletionRequestNotFoundError())
            await session.commit()
            return Ok(True)

    async def processDueDeletions(self, batch_size: int = 100) -> int:
        """Delete organizations whose grace period has expired."""
        now_utc = datetime.now(UTC)
        cutoff = now_utc - timedelta(
            days=getOrgSettings().deletion_cancel_window_days
        )
        processed = 0

        async with self.session_manager.get_session() as session:
            due_requests = await self.deletion_repo.listDueRequests(
                session=session,
                due_before_or_equal=cutoff,
                limit=batch_size,
            )

            for req in due_requests:
                org_id = req.org_id
                delete_res = await self.kc.deleteOrg(org_id)
                if delete_res.status == ResultStatus.Err and not isinstance(
                    delete_res.err(), OrgNotFoundError
                ):
                    self.logger.warning(
                        "org_delete_worker_failed",
                        org_id=org_id,
                        error=getattr(
                            delete_res.err(),
                            "detail",
                            str(delete_res.err()),
                        ),
                    )
                    continue

                await self.settings_repo.deleteByOrgId(session, org_id)
                await self.deletion_repo.deleteByOrgId(session, org_id)
                processed += 1
                self.logger.info(
                    "org_deleted_after_grace_period", org_id=org_id
                )

            if processed > 0:
                await session.commit()

        return processed

    # organization metadata
    async def getOrgInfo(
        self, org_id: str
    ) -> Result[
        OrgInfoResponse,
        OrgNotFoundError
        | MemberNotFoundError
        | KeycloakOrgError
        | OwnerNotFoundError
        | MultipleOwnersError,
    ]:
        """Return organization metadata enriched with resolved owner info."""
        return await self._syncMetadataFromKeycloak(org_id)

    async def listOrgs(
        self,
        limit: int = 20,
        offset: int = 0,
        q: str | None = None,
    ) -> Result[OrgListResponse, KeycloakOrgError]:
        """List organizations for admin dashboard consumers."""
        orgs_res = await self.kc.listOrgs(
            first=offset,
            max_results=limit,
            search=q,
        )
        if orgs_res.status == ResultStatus.Err:
            return orgs_res.into()
        orgs = cast(list[KeycloakOrgPayload], orgs_res.unwrap())

        return Ok(
            OrgListResponse(
                total=len(orgs),
                results=[
                    OrgInfoResponse(
                        org_id=str(org.get("id") or ""),
                        name=str(org.get("name") or org.get("alias") or ""),
                        alias=org.get("alias"),
                        owner_id=None,
                    )
                    for org in orgs
                    if org.get("id")
                ],
            )
        )

    async def listUserOrgs(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        q: str | None = None,
    ) -> Result[
        OrgListResponse,
        MemberNotFoundError | KeycloakOrgError,
    ]:
        """List organizations the current user belongs to, with local search."""
        orgs_res = await self.kc.getMemberOrganizations(user_id)
        if orgs_res.status == ResultStatus.Err:
            return orgs_res.into()

        orgs = [
            org
            for org in cast(list[KeycloakOrgPayload], orgs_res.unwrap())
            if org.get("id") and _matches_org_query(org, q)
        ]
        page = orgs[offset : offset + limit]
        return Ok(
            OrgListResponse(
                total=len(orgs),
                results=[
                    OrgInfoResponse(
                        org_id=str(org.get("id") or ""),
                        name=str(org.get("name") or org.get("alias") or ""),
                        alias=org.get("alias"),
                        owner_id=None,
                    )
                    for org in page
                ],
            )
        )

    async def createOrg(
        self,
        name: str,
        alias: str | None = None,
        owner_id: str | None = None,
    ) -> Result[
        OrgInfoResponse,
        KeycloakOrgError
        | MemberNotFoundError
        | OrgNotFoundError
        | UserAlreadyInAnotherOrganizationError
        | KeycloakPossibleError,
    ]:
        """Create an organization from the admin dashboard."""
        if owner_id:
            orgs_res = await self.kc.getMemberOrganizations(owner_id)
            if orgs_res.status == ResultStatus.Err:
                return orgs_res.into()

            org_ids = _extract_org_ids(orgs_res.unwrap())
            if org_ids:
                return Err(UserAlreadyInAnotherOrganizationError())

        payload: CreateOrgPayload = {"name": name}
        if alias:
            payload["alias"] = alias

        create_res = await self.kc.createOrg(payload)
        if create_res.status == ResultStatus.Err:
            return create_res.into()
        org_id = create_res.unwrap()

        if owner_id:
            add_res = await self.kc.addMember(org_id, owner_id)
            if add_res.status == ResultStatus.Err:
                return add_res.into()
            attr_res = await self.kc.setUserAttribute(
                owner_id,
                _ORG_PERM_ATTR,
                [OrgPermission.OWNER.value],
            )
            if attr_res.status == ResultStatus.Err:
                return attr_res.into()

        return Ok(
            OrgInfoResponse(
                org_id=org_id,
                name=name,
                alias=alias,
                owner_id=owner_id,
            )
        )

    async def updateOrgInfo(
        self,
        org_id: str,
        actor_user_id: str,
        name: str | None,
        alias: str | None = None,
    ) -> Result[
        OrgInfoResponse,
        OrgNotFoundError
        | MemberNotFoundError
        | KeycloakOrgError
        | OwnerNotFoundError
        | MultipleOwnersError
        | OwnerPermissionRequiredError,
    ]:
        """Update organization metadata after owner checks pass."""
        owner_id_res = await self._getOrgOwnerId(org_id)
        if owner_id_res.status == ResultStatus.Err:
            return owner_id_res.into()
        owner_id = owner_id_res.unwrap()
        if owner_id != actor_user_id:
            return Err(OwnerPermissionRequiredError())

        current_org_res = await self.kc.getOrg(org_id)
        if current_org_res.status == ResultStatus.Err:
            return current_org_res.into()
        current_org = current_org_res.unwrap()
        payload = dict(current_org)
        if name is not None:
            payload["name"] = name
        if alias is not None:
            payload["alias"] = alias

        update_res = await self.kc.updateOrg(org_id, payload)
        if update_res.status == ResultStatus.Err:
            return update_res.into()

        updated_name = str(payload.get("name") or payload.get("alias") or "")
        updated_alias = payload.get("alias")
        return Ok(
            OrgInfoResponse(
                org_id=org_id,
                name=updated_name,
                alias=str(updated_alias) if updated_alias is not None else None,
                owner_id=owner_id,
            )
        )

    # settings
    async def getSettings(
        self, org_id: str
    ) -> Result[OrgSettingsResponse, OrgNotFoundError | KeycloakOrgError]:
        """Fetch organization settings, creating an empty row when missing."""
        org_res = await self._ensureOrgExists(org_id)
        if org_res.status == ResultStatus.Err:
            return org_res.into()

        async with self.session_manager.get_session() as session:
            settings = await self.settings_repo.getOrCreate(session, org_id)
            output = OrgSettingsResponse(
                rate_limit=settings.rate_limit,
                spending_limit=settings.spending_limit,
                extra=settings.extra or {},
            )
            await session.commit()
            return Ok(output)

    async def updateSettings(
        self,
        org_id: str,
        rate_limit: int | None,
        spending_limit: int | None,
        extra: dict[str, Any],
    ) -> Result[OrgSettingsResponse, OrgNotFoundError | KeycloakOrgError]:
        """Persist organization settings after flattening nested extra data."""
        org_res = await self._ensureOrgExists(org_id)
        if org_res.status == ResultStatus.Err:
            return org_res.into()

        flattened_extra = self._flattenSettings(extra)

        async with self.session_manager.get_session() as session:
            settings = await self.settings_repo.upsert(
                session,
                org_id,
                rate_limit,
                spending_limit,
                flattened_extra,
            )
            output = OrgSettingsResponse(
                rate_limit=settings.rate_limit,
                spending_limit=settings.spending_limit,
                extra=settings.extra or {},
            )
            await session.commit()
            return Ok(output)

    # users
    async def getUsers(
        self,
        org_id: str,
        limit: int = 20,
        offset: int = 0,
        q: str | None = None,
    ) -> Result[OrgUserListResponse, OrgNotFoundError | KeycloakOrgError]:
        """List organization members with Keycloak-backed pagination metadata."""
        members_res = await self.kc.getOrgMembers(
            org_id, first=offset, max_results=limit, search=q
        )
        if members_res.status == ResultStatus.Err:
            return members_res.into()
        members = cast(list[KeycloakUserPayload], members_res.unwrap())

        count_res = await self.kc.getOrgMemberCount(org_id)
        total = count_res.unwrap_or(len(members))

        results = [
            OrgUserResponse(
                id=m.get("id", ""),
                username=m.get("username"),
                email=m.get("email"),
            )
            for m in members
        ]
        return Ok(OrgUserListResponse(total=total, results=results))

    async def removeUser(
        self, org_id: str, user_id: str
    ) -> Result[
        bool,
        OrgNotFoundError
        | MemberNotFoundError
        | KeycloakOrgError
        | OwnerNotFoundError
        | MultipleOwnersError
        | OwnerRemovalNotAllowedError,
    ]:
        """Remove a non-owner member from the organization and delete the user."""
        owner_id_res = await self._getOrgOwnerId(org_id)
        if owner_id_res.status == ResultStatus.Err:
            return owner_id_res.into()
        if user_id == owner_id_res.unwrap():
            return Err(OwnerRemovalNotAllowedError())

        remove_res = await self.kc.removeMember(org_id, user_id)
        if remove_res.status == ResultStatus.Err:
            return remove_res
        delete_res = await self.kc.deleteUser(user_id)
        if delete_res.status == ResultStatus.Ok:
            return delete_res
        if isinstance(delete_res.err(), MemberNotFoundError):
            return Ok(True)
        return delete_res

    # invitations
    async def getInvitations(
        self, org_id: str
    ) -> Result[
        InvitationListResponse,
        OrgNotFoundError | KeycloakOrgError | KeycloakPossibleError,
    ]:
        """List pending invitations for an organization."""
        inv_res = await self.kc.getInvitations(org_id)
        if inv_res.status == ResultStatus.Err:
            return inv_res.into()
        raw_list = cast(list[KeycloakInvitationPayload], inv_res.unwrap())

        results = []
        for inv in raw_list:
            results.append(
                InvitationResponse(
                    id=str(inv.get("id", "")),
                    email=inv.get("email", ""),
                    status=inv.get("status"),
                )
            )
        return Ok(InvitationListResponse(results=results))

    async def getInvitation(
        self, org_id: str, invitation_id: str
    ) -> Result[
        InvitationResponse,
        InvitationNotFoundError | KeycloakOrgError | KeycloakPossibleError,
    ]:
        """Fetch one invitation and map it into the public DTO."""
        inv_res = await self.kc.getInvitation(org_id, invitation_id)
        if inv_res.status == ResultStatus.Err:
            return inv_res.into()
        inv = cast(KeycloakInvitationPayload, inv_res.unwrap())

        return Ok(
            InvitationResponse(
                id=str(inv.get("id", "")),
                email=inv.get("email", ""),
                status=inv.get("status"),
            )
        )

    async def createInvitation(
        self,
        org_id: str,
        email: str,
    ) -> Result[
        bool,
        KeycloakOrgError
        | OrgNotFoundError
        | MemberNotFoundError
        | UserAlreadyInOrganizationError
        | UserAlreadyInAnotherOrganizationError
        | KeycloakPossibleError,
    ]:
        """Invite a user after enforcing the one-user-one-org invariant."""
        existing_user_res = await self.kc.findUserByEmail(email)
        if existing_user_res.status == ResultStatus.Err:
            return existing_user_res.into()
        existing_user = existing_user_res.unwrap()
        if existing_user and existing_user.get("id"):
            existing_user_id = str(existing_user["id"])
            orgs_res = await self.kc.getMemberOrganizations(existing_user_id)
            if orgs_res.status == ResultStatus.Err:
                return orgs_res.into()

            org_ids = _extract_org_ids(orgs_res.unwrap())
            if org_id in org_ids:
                return Err(UserAlreadyInOrganizationError())
            if org_ids:
                return Err(UserAlreadyInAnotherOrganizationError())

        settings = getOrgSettings()
        invite_res = await self.kc.inviteUser(
            org_id,
            email,
            client_id=settings.invite_client_id,
            redirect_uri=settings.invite_redirect_uri,
        )
        if invite_res.status == ResultStatus.Err:
            return invite_res.into()
        return Ok(True)

    async def deleteInvitation(
        self, org_id: str, invitation_id: str
    ) -> Result[
        bool, InvitationNotFoundError | KeycloakOrgError | KeycloakPossibleError
    ]:
        """Delete an existing invitation."""
        return await self.kc.deleteInvitation(org_id, invitation_id)

    async def resendInvitation(
        self, org_id: str, invitation_id: str
    ) -> Result[
        InvitationResponse,
        InvitationNotFoundError
        | OrgNotFoundError
        | KeycloakOrgError
        | KeycloakPossibleError,
    ]:
        """Resend an invitation and return the replacement Keycloak record."""
        old_inv_res = await self.kc.getInvitation(org_id, invitation_id)
        if old_inv_res.status == ResultStatus.Err:
            return old_inv_res.into()

        old_inv = cast(KeycloakInvitationPayload, old_inv_res.unwrap())
        email = str(old_inv.get("email", "")).strip()
        if not email:
            return Err(InvitationNotFoundError())

        resend_res = await self.kc.resendInvitation(org_id, invitation_id)
        if resend_res.status == ResultStatus.Err:
            return resend_res.into()

        new_inv_res = await self.kc.getInvitations(org_id, email=email)
        if new_inv_res.status == ResultStatus.Err:
            return new_inv_res.into()

        raw_list = cast(list[KeycloakInvitationPayload], new_inv_res.unwrap())
        new_inv = next(
            (
                inv
                for inv in raw_list
                if str(inv.get("email", "")).casefold() == email.casefold()
            ),
            None,
        )
        if new_inv is None:
            return Err(InvitationNotFoundError())

        return Ok(
            InvitationResponse(
                id=str(new_inv.get("id", "")),
                email=new_inv.get("email", ""),
                status=new_inv.get("status"),
            )
        )

    # user permissions
    async def ensureCanReadUserPermissions(
        self,
        org_id: str,
        actor_user_id: str,
        target_user_id: str,
    ) -> Result[
        None,
        MemberNotFoundError
        | KeycloakOrgError
        | MultipleOrganizationMembershipError
        | UserNotInOrganizationError
        | ReadOwnPermissionsOrManageRequiredError,
    ]:
        """Authorize reading organization permissions for the target user."""
        target_member_res = await self._ensureUserInOrg(org_id, target_user_id)
        if target_member_res.status == ResultStatus.Err:
            return target_member_res.into()

        if actor_user_id == target_user_id:
            return Ok(None)

        actor_perms_res = await self._getMemberPermissions(
            org_id, actor_user_id
        )
        if actor_perms_res.status == ResultStatus.Err:
            return actor_perms_res.into()

        if not has_permission(
            actor_perms_res.unwrap(),
            OrgPermission.USERS_PERMISSIONS_RW,
        ):
            return Err(ReadOwnPermissionsOrManageRequiredError())

        return Ok(None)

    async def getUserPermissions(
        self, org_id: str, user_id: str
    ) -> Result[
        UserPermissionsResponse,
        MemberNotFoundError
        | KeycloakOrgError
        | MultipleOrganizationMembershipError
        | UserNotInOrganizationError,
    ]:
        """Return normalized organization permissions for one user."""
        perms_res = await self._getMemberPermissions(org_id, user_id)
        if perms_res.status == ResultStatus.Err:
            return perms_res.into()
        return Ok(UserPermissionsResponse(permissions=perms_res.unwrap()))

    async def updateUserPermissions(
        self,
        org_id: str,
        actor_user_id: str,
        user_id: str,
        permissions: list[str],
    ) -> Result[
        UserPermissionsResponse,
        InvalidPermissionError
        | OrgNotFoundError
        | MemberNotFoundError
        | KeycloakOrgError
        | OwnerNotFoundError
        | MultipleOwnersError
        | OwnerPermissionImmutableError
        | OwnerTransferNotAllowedError
        | UserNotInOrganizationError
        | MultipleOrganizationMembershipError
        | OwnerRequiredForGrantError,
    ]:
        """Replace a member's organization permissions with invariant checks."""
        valid = {p.value for p in OrgPermission}
        invalid = set(permissions) - valid
        if invalid:
            return Err(InvalidPermissionError())

        owner_id_res = await self._getOrgOwnerId(org_id)
        if owner_id_res.status == ResultStatus.Err:
            return owner_id_res.into()
        owner_id = owner_id_res.unwrap()

        if user_id == owner_id and OrgPermission.OWNER.value not in permissions:
            return Err(OwnerPermissionImmutableError())
        if user_id != owner_id and OrgPermission.OWNER.value in permissions:
            return Err(OwnerTransferNotAllowedError())

        actor_perms_res = await self._getMemberPermissions(
            org_id, actor_user_id
        )
        if actor_perms_res.status == ResultStatus.Err:
            return actor_perms_res.into()
        actor_perms = actor_perms_res.unwrap()

        target_perms = actor_perms
        if user_id != actor_user_id:
            target_perms_res = await self._getMemberPermissions(org_id, user_id)
            if target_perms_res.status == ResultStatus.Err:
                return target_perms_res.into()
            target_perms = target_perms_res.unwrap()

        is_granting_permission_rw = (
            OrgPermission.USERS_PERMISSIONS_RW.value in permissions
            and OrgPermission.USERS_PERMISSIONS_RW.value not in target_perms
        )
        if is_granting_permission_rw and not has_permission(
            actor_perms, OrgPermission.OWNER
        ):
            return Err(OwnerRequiredForGrantError())

        target_member_res = await self._ensureUserInOrg(org_id, user_id)
        if target_member_res.status == ResultStatus.Err:
            return target_member_res.into()

        set_res = await self.kc.setUserAttribute(
            user_id, _ORG_PERM_ATTR, permissions
        )
        if set_res.status == ResultStatus.Err:
            return set_res.into()

        return Ok(UserPermissionsResponse(permissions=permissions))
