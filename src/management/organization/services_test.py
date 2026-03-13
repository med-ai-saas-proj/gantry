"""Unit tests for OrgService permission and owner invariants."""

import os
import unittest
from types import SimpleNamespace
from datetime import UTC, datetime
from contextlib import asynccontextmanager
from unittest.mock import Mock, AsyncMock

from safe_result import Ok, Err


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from src.management.organization.services import (  # noqa: E402
    OrgService,
    OrgNotFoundError,
    InvalidPermissionError,
    OwnerRequiredForGrantError,
    OwnerRemovalNotAllowedError,
    DeletionRequestNotFoundError,
    OwnerPermissionRequiredError,
    OwnerTransferNotAllowedError,
    DeletionAlreadyRequestedError,
    OwnerPermissionImmutableError,
    UserAlreadyInOrganizationError,
    MultipleOrganizationMembershipError,
    UserAlreadyInAnotherOrganizationError,
    ServiceAccountOrgCreateNotAllowedError,
    ReadOwnPermissionsOrManageRequiredError,
    _extract_org_ids,
)
from src.management.organization.permissions import OrgPermission  # noqa: E402


class _DummySessionManager:
    def __init__(self):
        self.session = Mock()
        self.session.commit = AsyncMock()
        self.session.flush = AsyncMock()
        self.session.refresh = AsyncMock()

    @asynccontextmanager
    async def get_session(self):
        yield self.session


class _DummyError(Exception):
    pass


class TestOrgServiceUnit(unittest.IsolatedAsyncioTestCase):
    """Unit-test business rules in OrgService with mocked collaborators."""

    def _make_service(self) -> OrgService:
        """Create OrgService with fully mocked dependencies."""
        self.session_manager = _DummySessionManager()
        return OrgService(
            kc_client=Mock(),
            settings_repo=Mock(),
            deletion_repo=Mock(),
            session_manager=self.session_manager,
            logger=Mock(),
        )

    def test_extract_org_ids_filters_missing(self):
        """Helper should return only non-empty org ids."""
        # Arrange
        orgs = [{"id": "a"}, {"name": "x"}, {"id": ""}, {"id": "b"}]

        # Act
        result = _extract_org_ids(orgs)

        # Assert
        self.assertEqual(result, {"a", "b"})

    def test_extract_user_permissions_supports_string_and_list(self):
        """Extractor should normalize string/list and ignore invalid types."""
        # Arrange
        service = self._make_service()

        # Act
        from_string = service._extract_user_permissions(
            {"org_permissions": "organization.owner"}
        )
        from_list = service._extract_user_permissions(
            {"org_permissions": ["organization.invite", 123]}
        )
        from_invalid = service._extract_user_permissions(
            {"org_permissions": {"x": "y"}}
        )

        # Assert
        self.assertEqual(from_string, ["organization.owner"])
        self.assertEqual(from_list, ["organization.invite"])
        self.assertEqual(from_invalid, [])

    def test_flatten_settings_nested(self):
        """Nested settings should be flattened into dot-notation keys."""
        # Arrange
        service = self._make_service()
        data = {"a": {"b": {"c": 1}}, "x": 2}

        # Act
        flattened = service._flatten_settings(data)

        # Assert
        self.assertEqual(flattened, {"a.b.c": 1, "x": 2})

    async def test_ensure_user_in_org_multiple_memberships_denied(self):
        """User in multiple orgs should fail single-org invariant."""
        # Arrange
        service = self._make_service()
        service.kc.get_member_organizations = AsyncMock(
            return_value=Ok([{"id": "org-1"}, {"id": "org-2"}])
        )

        # Act
        res = await service._ensure_user_in_org("org-1", "u1")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, MultipleOrganizationMembershipError)

    async def test_create_org_service_account_blocked(self):
        """Backend service-account actor should not create organization."""
        # Arrange
        service = self._make_service()

        # Act
        res = await service.create_org(
            name="Org X",
            actor_user_id="u1",
            actor_is_service_account=True,
            actor_client_id="med-ai-saas-backend",
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, ServiceAccountOrgCreateNotAllowedError)

    async def test_create_org_user_already_in_another_org(self):
        """Actor already belonging to an org cannot create another org."""
        # Arrange
        service = self._make_service()
        service.kc.get_member_organizations = AsyncMock(
            return_value=Ok([{"id": "existing-org"}])
        )

        # Act
        res = await service.create_org("Org X", "u1")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, UserAlreadyInAnotherOrganizationError)

    async def test_create_org_success(self):
        """Successful create should add actor as member and owner."""
        # Arrange
        service = self._make_service()
        service.kc.get_member_organizations = AsyncMock(return_value=Ok([]))
        service.kc.create_org = AsyncMock(
            return_value=Ok({"id": "org-1", "name": "Org X"})
        )
        service.kc.add_member = AsyncMock(return_value=Ok(True))
        service.kc.set_user_attribute = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.create_org("Org X", "u1")

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().id, "org-1")
        service.kc.add_member.assert_awaited_once_with("org-1", "u1")
        service.kc.set_user_attribute.assert_awaited_once()

    async def test_create_org_rolls_back_when_add_member_fails(self):
        """If add_member fails, service should delete created org."""
        # Arrange
        service = self._make_service()
        err = _DummyError("add member failed")
        service.kc.get_member_organizations = AsyncMock(return_value=Ok([]))
        service.kc.create_org = AsyncMock(
            return_value=Ok({"id": "org-1", "name": "Org X"})
        )
        service.kc.add_member = AsyncMock(return_value=Err(err))
        service.kc.delete_org = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.create_org("Org X", "u1")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIs(res.error, err)
        service.kc.delete_org.assert_awaited_once_with("org-1")

    async def test_ensure_can_read_user_permissions_self_allowed(self):
        """User should always be able to read their own org permissions."""
        # Arrange
        service = self._make_service()
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.ensure_can_read_user_permissions(
            org_id="org-1",
            actor_user_id="u1",
            target_user_id="u1",
        )

        # Assert
        self.assertTrue(res.is_ok())

    async def test_ensure_can_read_user_permissions_other_user_requires_rw(
        self,
    ):
        """Reading another user's permissions requires manage permission."""
        # Arrange
        service = self._make_service()
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))
        service._get_member_permissions = AsyncMock(
            return_value=Ok([OrgPermission.SETTINGS_READ.value])
        )

        # Act
        res = await service.ensure_can_read_user_permissions(
            org_id="org-1",
            actor_user_id="u1",
            target_user_id="u2",
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(
            res.error, ReadOwnPermissionsOrManageRequiredError
        )

    async def test_ensure_can_read_user_permissions_service_actor_bypass(self):
        """Trusted backend service-account should bypass read checks."""
        # Arrange
        service = self._make_service()

        # Act
        res = await service.ensure_can_read_user_permissions(
            org_id="org-1",
            actor_user_id="svc",
            target_user_id="u2",
            actor_is_service_account=True,
            actor_client_id="med-ai-saas-backend",
        )

        # Assert
        self.assertTrue(res.is_ok())

    async def test_update_user_permissions_rejects_invalid(self):
        """Service must reject unknown org permission values."""
        # Arrange
        service = self._make_service()

        # Act
        res = await service.update_user_permissions(
            org_id="org-1",
            actor_user_id="u1",
            user_id="u2",
            permissions=["organization.owner", "bogus.permission"],
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, InvalidPermissionError)

    async def test_update_user_permissions_owner_permission_immutable(self):
        """Owner cannot lose organization.owner permission."""
        # Arrange
        service = self._make_service()
        service._get_org_owner_id = AsyncMock(return_value=Ok("u1"))
        service._get_member_permissions = AsyncMock(
            return_value=Ok([OrgPermission.OWNER.value])
        )
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.update_user_permissions(
            org_id="org-1",
            actor_user_id="u1",
            user_id="u1",
            permissions=[OrgPermission.SETTINGS_READ.value],
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, OwnerPermissionImmutableError)

    async def test_update_user_permissions_owner_transfer_not_allowed(self):
        """Cannot assign organization.owner to a non-owner user."""
        # Arrange
        service = self._make_service()
        service._get_org_owner_id = AsyncMock(return_value=Ok("u-owner"))
        service._get_member_permissions = AsyncMock(
            return_value=Ok([OrgPermission.OWNER.value])
        )
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.update_user_permissions(
            org_id="org-1",
            actor_user_id="u-owner",
            user_id="u-other",
            permissions=[OrgPermission.OWNER.value],
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, OwnerTransferNotAllowedError)

    async def test_update_user_permissions_grant_rw_requires_owner(self):
        """Only org owner can grant users.permissions.read_write."""
        # Arrange
        service = self._make_service()
        service._get_org_owner_id = AsyncMock(return_value=Ok("owner"))
        service._get_member_permissions = AsyncMock(
            return_value=Ok([OrgPermission.SETTINGS_READ.value])
        )
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.update_user_permissions(
            org_id="org-1",
            actor_user_id="u-actor",
            user_id="u-target",
            permissions=[OrgPermission.USERS_PERMISSIONS_RW.value],
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, OwnerRequiredForGrantError)

    async def test_update_user_permissions_success(self):
        """Valid permission update should persist via Keycloak attribute."""
        # Arrange
        service = self._make_service()
        service._get_org_owner_id = AsyncMock(return_value=Ok("u-owner"))
        service._get_member_permissions = AsyncMock(
            return_value=Ok([OrgPermission.OWNER.value])
        )
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))
        service.kc.set_user_attribute = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.update_user_permissions(
            org_id="org-1",
            actor_user_id="u-owner",
            user_id="u-target",
            permissions=[OrgPermission.SETTINGS_READ.value],
        )

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(
            res.unwrap().permissions, [OrgPermission.SETTINGS_READ.value]
        )
        service.kc.set_user_attribute.assert_awaited_once()

    async def test_remove_owner_not_allowed(self):
        """Organization owner removal should be blocked."""
        # Arrange
        service = self._make_service()
        service._get_org_owner_id = AsyncMock(return_value=Ok("owner"))

        # Act
        res = await service.remove_user("org-1", "owner")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, OwnerRemovalNotAllowedError)

    async def test_request_delete_org_conflict_when_already_requested(self):
        """Requesting deletion twice should return conflict."""
        # Arrange
        service = self._make_service()
        service._ensure_org_exists = AsyncMock(return_value=Ok({"id": "org-1"}))
        service.deletion_repo.get_by_org_id = AsyncMock(
            return_value=SimpleNamespace(id=1)
        )

        # Act
        res = await service.request_delete_org("org-1")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, DeletionAlreadyRequestedError)

    async def test_request_delete_org_success(self):
        """Deletion request should return timestamps and commit."""
        # Arrange
        service = self._make_service()
        now = datetime(2026, 3, 13, 10, 0, tzinfo=UTC).replace(tzinfo=None)
        service._ensure_org_exists = AsyncMock(return_value=Ok({"id": "org-1"}))
        service.deletion_repo.get_by_org_id = AsyncMock(return_value=None)
        service.deletion_repo.upsert_request = AsyncMock(
            return_value=SimpleNamespace(requested_at=now)
        )

        # Act
        res = await service.request_delete_org("org-1")

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().org_id, "org-1")
        self.session_manager.session.commit.assert_awaited()

    async def test_cancel_delete_org_not_found(self):
        """Cancel should fail if there is no pending deletion request."""
        # Arrange
        service = self._make_service()
        service.deletion_repo.delete_by_org_id = AsyncMock(return_value=False)

        # Act
        res = await service.cancel_delete_org("org-1")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, DeletionRequestNotFoundError)

    async def test_update_org_info_requires_owner(self):
        """Non-owner actor cannot update org metadata."""
        # Arrange
        service = self._make_service()
        service._get_org_owner_id = AsyncMock(return_value=Ok("u-owner"))

        # Act
        res = await service.update_org_info(
            org_id="org-1",
            actor_user_id="u-not-owner",
            name="new-name",
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, OwnerPermissionRequiredError)

    async def test_get_settings_success(self):
        """Get settings should return repository values and commit session."""
        # Arrange
        service = self._make_service()
        service._ensure_org_exists = AsyncMock(return_value=Ok({"id": "org-1"}))
        service.settings_repo.get_or_create = AsyncMock(
            return_value=SimpleNamespace(rate_limit=100, extra={"a": 1})
        )

        # Act
        res = await service.get_settings("org-1")

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().rate_limit, 100)
        self.assertEqual(res.unwrap().extra, {"a": 1})

    async def test_update_settings_flattens_nested_extra(self):
        """Update settings should flatten nested extra keys before upsert."""
        # Arrange
        service = self._make_service()
        service._ensure_org_exists = AsyncMock(return_value=Ok({"id": "org-1"}))
        service.settings_repo.upsert = AsyncMock(
            return_value=SimpleNamespace(
                rate_limit=90,
                extra={"a.b": 1, "x": 2},
            )
        )

        # Act
        res = await service.update_settings(
            org_id="org-1",
            rate_limit=90,
            extra={"a": {"b": 1}, "x": 2},
        )

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().extra, {"a.b": 1, "x": 2})
        service.settings_repo.upsert.assert_awaited_once()

    async def test_create_invitation_conflict_when_user_already_in_org(self):
        """Inviting an existing member should return conflict."""
        # Arrange
        service = self._make_service()
        service.kc.find_user_by_email = AsyncMock(return_value=Ok({"id": "u1"}))
        service.kc.get_member_organizations = AsyncMock(
            return_value=Ok([{"id": "org-1"}])
        )

        # Act
        res = await service.create_invitation("org-1", "x@example.com")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, UserAlreadyInOrganizationError)

    async def test_create_invitation_conflict_when_user_in_other_org(self):
        """Inviting user from another org should return conflict."""
        # Arrange
        service = self._make_service()
        service.kc.find_user_by_email = AsyncMock(return_value=Ok({"id": "u1"}))
        service.kc.get_member_organizations = AsyncMock(
            return_value=Ok([{"id": "org-2"}])
        )

        # Act
        res = await service.create_invitation("org-1", "x@example.com")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, UserAlreadyInAnotherOrganizationError)

    async def test_create_invitation_success_for_new_email(self):
        """Inviting new email should call Keycloak invite endpoint."""
        # Arrange
        service = self._make_service()
        service.kc.find_user_by_email = AsyncMock(return_value=Ok(None))
        service.kc.invite_user = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.create_invitation("org-1", "new@example.com")

        # Assert
        self.assertTrue(res.is_ok())
        service.kc.invite_user.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
