"""Business-logic service for Organization operations.

Orchestrates the Keycloak admin client and Postgres repositories.
"""

from src.db.factories import AsyncSessionManager
from src.shared.custom_types.error_exception import RecoverableError

from .dtos import (
    OrgInfoOutput,
    OrgUserOutput,
    InvitationOutput,
    OrgProjectOutput,
    OrgSettingsOutput,
    OrgUserListOutput,
    CreateProjectInput,
    DeleteRequestOutput,
    InvitationListOutput,
    OrgProjectListOutput,
    UserPermissionsOutput,
    CancelDeleteRequestOutput,
)
from .models import OrgProject
from .settings import getOrgSettings
from .permissions import OrgPermission, has_permission
from .repositories import (
    OrgProjectRepository,
    OrgMetadataRepository,
    OrgSettingsRepository,
    OrgInvitationRepository,
    OrgDeletionRequestRepository,
)
from .keycloak_client import (
    OrgNotFoundError,
    KeycloakOrgClient,
    UserNotInOrganizationError,
)

from typing import Any
from datetime import datetime, timezone, timedelta

from safe_result import Ok, Err, Result
from structlog.stdlib import BoundLogger


_CANCEL_WINDOW_DAYS = 30
_ORG_PERM_ATTR = "org_permissions"


class DeletionAlreadyRequestedError(RecoverableError):
    status = 409
    code = "deletion_already_requested"
    title = "Deletion Already Requested"
    detail = "A deletion request for this organization already exists."


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


class DeleteRequestNotFoundError(RecoverableError):
    status = 404
    code = "deletion_request_not_found"
    title = "Deletion Request Not Found"
    detail = "No pending deletion request exists for this organization."


class MultipleOrganizationMembershipError(RecoverableError):
    status = 409
    code = "multiple_org_membership_not_allowed"
    title = "Multiple Organization Membership Not Allowed"
    detail = "A user can belong to only one organization."


class OrgService:
    """Organisation feature service."""

    def __init__(
        self,
        kc_client: KeycloakOrgClient,
        settings_repo: OrgSettingsRepository,
        metadata_repo: OrgMetadataRepository,
        deletion_repo: OrgDeletionRequestRepository,
        project_repo: OrgProjectRepository,
        invitation_repo: OrgInvitationRepository,
        session_manager: AsyncSessionManager,
        logger: BoundLogger,
    ):
        self.kc = kc_client
        self.settings_repo = settings_repo
        self.metadata_repo = metadata_repo
        self.deletion_repo = deletion_repo
        self.project_repo = project_repo
        self.invitation_repo = invitation_repo
        self.session_manager = session_manager
        self.logger = logger

    async def _ensure_org_exists(
        self, org_id: str
    ) -> Result[dict[str, Any], RecoverableError]:
        return await self.kc.get_org(org_id)

    async def _ensure_user_in_org(
        self, org_id: str, user_id: str
    ) -> Result[bool, RecoverableError]:
        orgs_res = await self.kc.get_member_organizations(user_id)
        if orgs_res.is_err():
            return orgs_res

        orgs = orgs_res.unwrap()
        unique_org_ids = {
            str(org.get("id", "")) for org in orgs if org.get("id")
        }
        if len(unique_org_ids) > 1:
            return Err(MultipleOrganizationMembershipError())
        for org in orgs:
            if org.get("id") == org_id:
                return Ok(True)
        return Err(UserNotInOrganizationError())

    def _extract_user_permissions(self, attrs: dict[str, Any]) -> list[str]:
        # Keycloak user-profile validation allows org_permissions.
        legacy = attrs.get(_ORG_PERM_ATTR, [])
        if isinstance(legacy, str):
            legacy = [legacy]
        if isinstance(legacy, list):
            return [p for p in legacy if isinstance(p, str)]
        return []

    def _flatten_settings(
        self,
        data: dict[str, Any],
        prefix: str = "",
    ) -> dict[str, Any]:
        """Flatten nested settings to dot-notation keys."""
        flattened: dict[str, Any] = {}
        for key, value in data.items():
            final_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                flattened.update(
                    self._flatten_settings(value, prefix=final_key)
                )
            else:
                flattened[final_key] = value
        return flattened

    async def _get_member_permissions(
        self, org_id: str, user_id: str
    ) -> Result[list[str], RecoverableError]:
        member_res = await self._ensure_user_in_org(org_id, user_id)
        if member_res.is_err():
            return member_res

        attrs_res = await self.kc.get_user_attributes(user_id)
        if attrs_res.is_err():
            return attrs_res
        attrs = attrs_res.unwrap()
        return Ok(self._extract_user_permissions(attrs))

    async def _get_org_owner_id(
        self, org_id: str
    ) -> Result[str, RecoverableError]:
        async with self.session_manager.get_session() as session:
            metadata = await self.metadata_repo.get(session, org_id)
            if metadata is not None and metadata.owner_id:
                owner_id = metadata.owner_id
                await session.commit()
                return Ok(owner_id)
            await session.commit()

        first = 0
        max_results = 100
        owners: list[str] = []

        while True:
            members_res = await self.kc.get_org_members(
                org_id, first=first, max_results=max_results
            )
            if members_res.is_err():
                return members_res
            members = members_res.unwrap()
            if not members:
                break

            for member in members:
                member_id = member.get("id")
                if not member_id:
                    continue
                attrs_res = await self.kc.get_user_attributes(member_id)
                if attrs_res.is_err():
                    return attrs_res
                perms = self._extract_user_permissions(attrs_res.unwrap())
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
        owner_id = unique_owners[0]

        org_res = await self.kc.get_org(org_id)
        if org_res.is_err():
            return org_res
        org_name = str(org_res.unwrap().get("name") or org_id)

        async with self.session_manager.get_session() as session:
            await self.metadata_repo.upsert(
                session=session,
                org_id=org_id,
                name=org_name,
                owner_id=owner_id,
            )
            await session.commit()
        return Ok(owner_id)

    async def _sync_metadata_from_keycloak(
        self, org_id: str
    ) -> Result[OrgInfoOutput, RecoverableError]:
        org_res = await self.kc.get_org(org_id)
        if org_res.is_err():
            return org_res
        org = org_res.unwrap()
        name = str(org.get("name") or org_id)

        owner_id_res = await self._get_org_owner_id(org_id)
        if owner_id_res.is_err():
            return owner_id_res
        owner_id = owner_id_res.unwrap()

        async with self.session_manager.get_session() as session:
            metadata = await self.metadata_repo.upsert(
                session=session,
                org_id=org_id,
                name=name,
                owner_id=owner_id,
            )
            output = OrgInfoOutput(
                id=metadata.org_id,
                name=metadata.name,
                owner_id=metadata.owner_id,
            )
            await session.commit()
            return Ok(output)

    # delete org
    async def request_delete_org(
        self, org_id: str, user_id: str
    ) -> Result[DeleteRequestOutput, RecoverableError]:
        org_res = await self._ensure_org_exists(org_id)
        if org_res.is_err():
            return org_res

        async with self.session_manager.get_session() as session:
            existing = await self.deletion_repo.get_by_org_id(session, org_id)
            if existing is not None:
                return Err(DeletionAlreadyRequestedError())

            now = datetime.now(timezone.utc).replace(tzinfo=None)
            cancel_before = now + timedelta(days=_CANCEL_WINDOW_DAYS)

            await self.deletion_repo.upsert_request(
                session=session,
                org_id=org_id,
                requested_by=user_id,
                cancel_before=cancel_before,
            )
            await session.commit()

            return Ok(
                DeleteRequestOutput(
                    org_id=org_id,
                    cancel_before=cancel_before.isoformat(),
                )
            )

    async def cancel_delete_org(
        self, org_id: str
    ) -> Result[CancelDeleteRequestOutput, RecoverableError]:
        org_res = await self._ensure_org_exists(org_id)
        if org_res.is_err():
            return org_res

        async with self.session_manager.get_session() as session:
            record = await self.deletion_repo.cancel_by_org_id(session, org_id)
            if record is None:
                return Err(DeleteRequestNotFoundError())
            await session.commit()
            return Ok(
                CancelDeleteRequestOutput(
                    org_id=org_id,
                    cancelled=True,
                )
            )

    async def process_due_deletions(
        self,
        now: datetime | None = None,
    ) -> Result[int, RecoverableError]:
        current = now or datetime.now(timezone.utc).replace(tzinfo=None)
        deleted = 0

        async with self.session_manager.get_session() as session:
            due = await self.deletion_repo.list_due(session, current)
            for req in due:
                org_id = req.org_id
                delete_org_res = await self.kc.delete_org(org_id)
                if delete_org_res.is_err():
                    err = delete_org_res.error
                    if not isinstance(err, OrgNotFoundError):
                        continue

                await self.project_repo.delete_by_org_id(session, org_id)
                await self.invitation_repo.delete_by_org_id(session, org_id)
                await self.settings_repo.deleteByKey(session, org_id)
                await self.metadata_repo.delete_by_org_id(session, org_id)
                await self.deletion_repo.delete_by_org_id(session, org_id)
                deleted += 1

            await session.commit()

        return Ok(deleted)

    # organization metadata
    async def get_org_info(
        self, org_id: str
    ) -> Result[OrgInfoOutput, RecoverableError]:
        return await self._sync_metadata_from_keycloak(org_id)

    async def update_org_info(
        self,
        org_id: str,
        actor_user_id: str,
        name: str,
    ) -> Result[OrgInfoOutput, RecoverableError]:
        owner_id_res = await self._get_org_owner_id(org_id)
        if owner_id_res.is_err():
            return owner_id_res
        if owner_id_res.unwrap() != actor_user_id:
            return Err(OwnerPermissionRequiredError())

        current_org_res = await self.kc.get_org(org_id)
        if current_org_res.is_err():
            return current_org_res
        current_org = current_org_res.unwrap()
        payload = {**current_org, "name": name}

        update_res = await self.kc.update_org(org_id, payload)
        if update_res.is_err():
            return update_res

        async with self.session_manager.get_session() as session:
            metadata = await self.metadata_repo.upsert(
                session=session,
                org_id=org_id,
                name=name,
                owner_id=owner_id_res.unwrap(),
            )
            output = OrgInfoOutput(
                id=metadata.org_id,
                name=metadata.name,
                owner_id=metadata.owner_id,
            )
            await session.commit()
            return Ok(output)

    # projects
    async def get_projects(
        self,
        org_id: str,
        limit: int = 20,
        offset: int = 0,
        q: str | None = None,
    ) -> Result[OrgProjectListOutput, RecoverableError]:
        org_res = await self._ensure_org_exists(org_id)
        if org_res.is_err():
            return org_res

        async with self.session_manager.get_session() as session:
            projects = await self.project_repo.get_by_org_id(
                session, org_id, limit=limit, offset=offset, q=q
            )
            total = await self.project_repo.count_by_org_id(session, org_id)
            await session.commit()

        results = [
            OrgProjectOutput(
                id=str(project.id),
                name=project.name,
                description=project.description,
            )
            for project in projects
        ]
        return Ok(OrgProjectListOutput(total=total, results=results))

    async def create_project(
        self,
        org_id: str,
        input_data: CreateProjectInput,
    ) -> Result[OrgProjectOutput, RecoverableError]:
        org_res = await self._ensure_org_exists(org_id)
        if org_res.is_err():
            return org_res

        async with self.session_manager.get_session() as session:
            project = OrgProject(
                org_id=org_id,
                name=input_data.name,
                description=input_data.description,
            )
            project = await self.project_repo.create(session, project)
            output = OrgProjectOutput(
                id=str(project.id),
                name=project.name,
                description=project.description,
            )
            await session.commit()

        return Ok(output)

    # settings
    async def get_settings(
        self, org_id: str
    ) -> Result[OrgSettingsOutput, RecoverableError]:
        org_res = await self._ensure_org_exists(org_id)
        if org_res.is_err():
            return org_res

        async with self.session_manager.get_session() as session:
            settings = await self.settings_repo.get_or_create(session, org_id)
            output = OrgSettingsOutput(
                rate_limit=settings.rate_limit,
                extra=settings.extra or {},
            )
            await session.commit()
            return Ok(output)

    async def update_settings(
        self,
        org_id: str,
        rate_limit: int | None,
        extra: dict[str, Any],
    ) -> Result[OrgSettingsOutput, RecoverableError]:
        org_res = await self._ensure_org_exists(org_id)
        if org_res.is_err():
            return org_res

        flattened_extra = self._flatten_settings(extra)

        async with self.session_manager.get_session() as session:
            settings = await self.settings_repo.upsert(
                session, org_id, rate_limit, flattened_extra
            )
            output = OrgSettingsOutput(
                rate_limit=settings.rate_limit,
                extra=settings.extra or {},
            )
            await session.commit()
            return Ok(output)

    # users
    async def get_users(
        self,
        org_id: str,
        limit: int = 20,
        offset: int = 0,
        q: str | None = None,
    ) -> Result[OrgUserListOutput, RecoverableError]:
        members_res = await self.kc.get_org_members(
            org_id, first=offset, max_results=limit, search=q
        )
        if members_res.is_err():
            return members_res
        members = members_res.unwrap()

        count_res = await self.kc.get_org_member_count(org_id)
        total = count_res.unwrap() if count_res.is_ok() else len(members)

        results = [
            OrgUserOutput(
                id=m.get("id", ""),
                username=m.get("username"),
                email=m.get("email"),
            )
            for m in members
        ]
        return Ok(OrgUserListOutput(total=total, results=results))

    async def remove_user(
        self, org_id: str, user_id: str
    ) -> Result[bool, RecoverableError]:
        owner_id_res = await self._get_org_owner_id(org_id)
        if owner_id_res.is_err():
            return owner_id_res
        if user_id == owner_id_res.unwrap():
            return Err(OwnerRemovalNotAllowedError())

        remove_res = await self.kc.remove_member(org_id, user_id)
        if remove_res.is_err():
            return remove_res
        return await self.kc.delete_user(user_id)

    # invitations
    async def get_invitations(
        self, org_id: str
    ) -> Result[InvitationListOutput, RecoverableError]:
        inv_res = await self.kc.get_invitations(org_id)
        if inv_res.is_err():
            return inv_res
        raw_list = inv_res.unwrap()

        async with self.session_manager.get_session() as session:
            db_invs = await self.invitation_repo.get_by_org_id(session, org_id)
            permissions_by_email = {
                inv.email: list(inv.permissions or []) for inv in db_invs
            }
            await session.commit()

        results = []
        for inv in raw_list:
            email = inv.get("email", "")
            permissions = permissions_by_email.get(email, [])
            results.append(
                InvitationOutput(
                    id=str(inv.get("id", "")),
                    email=email,
                    status=inv.get("status"),
                    permissions=permissions,
                )
            )
        return Ok(InvitationListOutput(results=results))

    async def get_invitation(
        self, org_id: str, invitation_id: str
    ) -> Result[InvitationOutput, RecoverableError]:
        inv_res = await self.kc.get_invitation(org_id, invitation_id)
        if inv_res.is_err():
            return inv_res
        inv = inv_res.unwrap()

        permissions: list[str] = []
        email = inv.get("email", "")
        if email:
            async with self.session_manager.get_session() as session:
                db_inv = await self.invitation_repo.get_by_org_and_email(
                    session, org_id, email
                )
                if db_inv is not None:
                    permissions = list(db_inv.permissions or [])
                await session.commit()

        return Ok(
            InvitationOutput(
                id=str(inv.get("id", "")),
                email=email,
                status=inv.get("status"),
                permissions=permissions,
            )
        )

    async def create_invitation(
        self,
        org_id: str,
        email: str,
        permissions: list[str],
        invited_by: str | None = None,
    ) -> Result[bool, RecoverableError]:
        valid = {p.value for p in OrgPermission}
        invalid = set(permissions) - valid
        if invalid:
            return Err(InvalidPermissionError())

        existing_user_res = await self.kc.find_user_by_email(email)
        if existing_user_res.is_err():
            return existing_user_res
        existing_user = existing_user_res.unwrap()
        if existing_user and existing_user.get("id"):
            existing_user_id = str(existing_user["id"])
            orgs_res = await self.kc.get_member_organizations(existing_user_id)
            if orgs_res.is_ok():
                org_ids = {
                    str(org.get("id", ""))
                    for org in orgs_res.unwrap()
                    if org.get("id")
                }
                if org_id in org_ids:
                    return Err(UserAlreadyInOrganizationError())
                if org_ids:
                    return Err(UserAlreadyInAnotherOrganizationError())

        invite_res = await self.kc.invite_user(org_id, email)
        if invite_res.is_err():
            return invite_res

        async with self.session_manager.get_session() as session:
            await self.invitation_repo.upsert_by_org_email(
                session=session,
                org_id=org_id,
                email=email,
                invited_by=invited_by,
                permissions=permissions,
            )
            await session.commit()
        return Ok(True)

    async def delete_invitation(
        self, org_id: str, invitation_id: str
    ) -> Result[bool, RecoverableError]:
        inv_res = await self.kc.get_invitation(org_id, invitation_id)
        if inv_res.is_err():
            return inv_res
        email = inv_res.unwrap().get("email", "")

        delete_res = await self.kc.delete_invitation(org_id, invitation_id)
        if delete_res.is_err():
            return delete_res

        if email:
            async with self.session_manager.get_session() as session:
                await self.invitation_repo.delete_by_org_and_email(
                    session, org_id, email
                )
                await session.commit()

        return Ok(True)

    async def resend_invitation(
        self, org_id: str, invitation_id: str
    ) -> Result[bool, RecoverableError]:
        return await self.kc.resend_invitation(org_id, invitation_id)

    # user permissions
    async def ensure_can_read_user_permissions(
        self,
        org_id: str,
        actor_user_id: str,
        target_user_id: str,
    ) -> Result[None, RecoverableError]:
        target_member_res = await self._ensure_user_in_org(
            org_id, target_user_id
        )
        if target_member_res.is_err():
            return target_member_res

        if actor_user_id == target_user_id:
            return Ok(None)

        actor_perms_res = await self._get_member_permissions(
            org_id, actor_user_id
        )
        if actor_perms_res.is_err():
            return actor_perms_res

        if not has_permission(
            actor_perms_res.unwrap(),
            OrgPermission.USERS_PERMISSIONS_RW,
        ):
            return Err(ReadOwnPermissionsOrManageRequiredError())

        return Ok(None)

    async def get_user_permissions(
        self, org_id: str, user_id: str
    ) -> Result[UserPermissionsOutput, RecoverableError]:
        perms_res = await self._get_member_permissions(org_id, user_id)
        if perms_res.is_err():
            return perms_res
        return Ok(UserPermissionsOutput(permissions=perms_res.unwrap()))

    async def update_user_permissions(
        self,
        org_id: str,
        actor_user_id: str,
        user_id: str,
        permissions: list[str],
    ) -> Result[UserPermissionsOutput, RecoverableError]:
        valid = {p.value for p in OrgPermission}
        invalid = set(permissions) - valid
        if invalid:
            return Err(InvalidPermissionError())

        owner_id_res = await self._get_org_owner_id(org_id)
        if owner_id_res.is_err():
            return owner_id_res
        owner_id = owner_id_res.unwrap()

        if user_id == owner_id and OrgPermission.OWNER.value not in permissions:
            return Err(OwnerPermissionImmutableError())
        if user_id != owner_id and OrgPermission.OWNER.value in permissions:
            return Err(OwnerTransferNotAllowedError())

        actor_perms_res = await self._get_member_permissions(
            org_id, actor_user_id
        )
        if actor_perms_res.is_err():
            return actor_perms_res
        actor_perms = actor_perms_res.unwrap()

        if (
            OrgPermission.USERS_PERMISSIONS_RW.value in permissions
            and not has_permission(actor_perms, OrgPermission.OWNER)
        ):
            return Err(OwnerRequiredForGrantError())

        target_member_res = await self._ensure_user_in_org(org_id, user_id)
        if target_member_res.is_err():
            return target_member_res

        set_res = await self.kc.set_user_attribute(
            user_id, _ORG_PERM_ATTR, permissions
        )
        if set_res.is_err():
            return set_res

        return Ok(UserPermissionsOutput(permissions=permissions))

    # rate limit (exported dependency)
    async def get_limit(self, org_id: str) -> int | None:
        """Return the effective rate limit for the org.

        Falls back to the global default when the org has no override.
        """
        async with self.session_manager.get_session() as session:
            settings = await self.settings_repo.get_or_create(session, org_id)
            limit = settings.rate_limit
            await session.commit()
            if limit is not None:
                return limit
        return getOrgSettings().default_rate_limit
