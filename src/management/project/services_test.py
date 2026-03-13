"""Unit tests for ProjectService rules using mocked dependencies."""

import os
import unittest
from types import SimpleNamespace
from contextlib import asynccontextmanager
from unittest.mock import Mock, AsyncMock

from safe_result import Ok, Err


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from src.management.project.services import (  # noqa: E402
    ProjectService,
    ProjectArchivedError,
    ProjectNotFoundError,
    UserNotInProjectError,
    UserAlreadyInProjectError,
    OwnerRequiredForGrantError,
    InvalidProjectPermissionError,
    LastOwnerRemovalNotAllowedError,
    InsufficientProjectPermissionError,
)
from src.management.project.permissions import ProjectPermission  # noqa: E402


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


class TestProjectServiceUnit(unittest.IsolatedAsyncioTestCase):
    """Unit-test project business rules without external services."""

    def _make_service(self) -> ProjectService:
        """Create ProjectService with mocked repos and Keycloak client."""
        self.session_manager = _DummySessionManager()
        return ProjectService(
            session_manager=self.session_manager,
            logger=Mock(),
            project_repo=Mock(),
            membership_repo=Mock(),
            kc_client=Mock(),
        )

    async def test_ensure_user_in_org_success_and_not_found(self):
        """Membership lookup should return Ok for matching org else error."""
        # Arrange
        service = self._make_service()
        service.kc.get_member_organizations = AsyncMock(
            return_value=Ok([{"id": "org-1"}])
        )

        # Act
        ok_res = await service._ensure_user_in_org("u1", "org-1")

        # Assert
        self.assertTrue(ok_res.is_ok())

        # Arrange
        service.kc.get_member_organizations = AsyncMock(
            return_value=Ok([{"id": "org-2"}])
        )

        # Act
        err_res = await service._ensure_user_in_org("u1", "org-1")

        # Assert
        self.assertTrue(err_res.is_err())

    async def test_get_project_or_err_not_found(self):
        """Unknown project uuid should return project_not_found."""
        # Arrange
        service = self._make_service()
        service.project_repo.get_by_uuid = AsyncMock(return_value=None)

        # Act
        res = await service._get_project_or_err("missing")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, ProjectNotFoundError)

    def test_ensure_project_active_helper(self):
        """Archived project should be rejected by helper."""
        # Arrange
        service = self._make_service()

        # Act
        ok_res = service._ensure_project_active(SimpleNamespace(archived=False))
        err_res = service._ensure_project_active(SimpleNamespace(archived=True))

        # Assert
        self.assertTrue(ok_res.is_ok())
        self.assertTrue(err_res.is_err())
        self.assertIsInstance(err_res.error, ProjectArchivedError)

    async def test_authorize_project_permission_denied(self):
        """Authorization should fail when member lacks required permission."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((1, "org-1", active_info))
        )
        service._get_member_permissions = AsyncMock(return_value=Ok([]))

        # Act
        result = await service.authorize_project_permission(
            "project-uuid",
            "u1",
            ProjectPermission.USERS_GET_ALL,
        )

        # Assert
        self.assertTrue(result.is_err())
        self.assertIsInstance(result.error, InsufficientProjectPermissionError)

    async def test_create_project_requires_projects_create(self):
        """Create project should fail if actor lacks projects.create scope."""
        # Arrange
        service = self._make_service()
        service._has_org_wide_project_permission = AsyncMock(
            return_value=Ok(False)
        )

        # Act
        res = await service.create_project("u1", "org-1", "p1", None)

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, InsufficientProjectPermissionError)

    async def test_list_user_projects_org_membership_error(self):
        """List by organization should fail if actor not in org."""
        # Arrange
        service = self._make_service()
        service._ensure_user_in_org = AsyncMock(
            return_value=Err(_DummyError("not in org"))
        )

        # Act
        res = await service.list_user_projects("u1", "org-1")

        # Assert
        self.assertTrue(res.is_err())

    async def test_list_user_projects_success(self):
        """List user projects should map repository rows to DTO."""
        # Arrange
        service = self._make_service()
        service.project_repo.list_by_member = AsyncMock(
            return_value=[
                SimpleNamespace(
                    uuid="p1",
                    name="P1",
                    description="d1",
                    organization_id="org-1",
                    is_archived=False,
                )
            ]
        )

        # Act
        res = await service.list_user_projects("u1", None)

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().total, 1)
        self.assertEqual(res.unwrap().results[0].name, "P1")

    async def test_has_org_wide_permission_true_and_false(self):
        """Org-wide permission check should respect membership permissions."""
        # Arrange
        service = self._make_service()
        service.membership_repo.list_memberships_for_user_in_org = AsyncMock(
            return_value=[
                SimpleNamespace(permissions=["project.settings.read"]),
                SimpleNamespace(permissions=["projects.get_all"]),
            ]
        )

        # Act
        true_res = await service._has_org_wide_project_permission(
            "u1", "org-1", ProjectPermission.PROJECTS_GET_ALL
        )

        # Assert
        self.assertTrue(true_res.is_ok())
        self.assertTrue(true_res.unwrap())

        # Arrange
        service.membership_repo.list_memberships_for_user_in_org = AsyncMock(
            return_value=[
                SimpleNamespace(permissions=["project.settings.read"])
            ]
        )

        # Act
        false_res = await service._has_org_wide_project_permission(
            "u1", "org-1", ProjectPermission.PROJECTS_CREATE
        )

        # Assert
        self.assertTrue(false_res.is_ok())
        self.assertFalse(false_res.unwrap())

    async def test_list_org_projects_success(self):
        """Org project list should return DTO when actor has permission."""
        # Arrange
        service = self._make_service()
        service._has_org_wide_project_permission = AsyncMock(
            return_value=Ok(True)
        )
        service.project_repo.list_by_org = AsyncMock(
            return_value=[
                SimpleNamespace(
                    uuid="p1",
                    name="P1",
                    description=None,
                    organization_id="org-1",
                    is_archived=False,
                )
            ]
        )

        # Act
        res = await service.list_org_projects("u1", "org-1")

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().total, 1)

    async def test_add_user_duplicate(self):
        """Adding an existing member should return duplicate error."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._ensure_user_in_org = AsyncMock(return_value=Ok(None))
        service.membership_repo.get_membership = AsyncMock(
            return_value=SimpleNamespace(user_id="u2")
        )

        # Act
        res = await service.add_user_to_project("proj-1", "u2")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, UserAlreadyInProjectError)

    async def test_add_user_success(self):
        """Adding new user should create membership and commit."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._ensure_user_in_org = AsyncMock(return_value=Ok(None))
        service.membership_repo.get_membership = AsyncMock(return_value=None)
        service.membership_repo.upsert_membership = AsyncMock(
            return_value=SimpleNamespace()
        )

        # Act
        res = await service.add_user_to_project("proj-1", "u2")

        # Assert
        self.assertTrue(res.is_ok())
        self.membership_repo = service.membership_repo
        self.membership_repo.upsert_membership.assert_awaited_once()
        self.session_manager.session.commit.assert_awaited()

    async def test_remove_last_owner_blocked(self):
        """Service must block removing the last project owner."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service.membership_repo.get_membership = AsyncMock(
            return_value=SimpleNamespace(permissions=["project.owner"])
        )
        service.membership_repo.count_owners = AsyncMock(return_value=1)

        # Act
        res = await service.remove_user_from_project("proj-1", "u-owner")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, LastOwnerRemovalNotAllowedError)

    async def test_remove_user_success(self):
        """Removing a non-owner member should succeed and commit."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service.membership_repo.get_membership = AsyncMock(
            return_value=SimpleNamespace(permissions=["project.settings.read"])
        )
        service.membership_repo.delete_membership = AsyncMock(return_value=True)

        # Act
        res = await service.remove_user_from_project("proj-1", "u2")

        # Assert
        self.assertTrue(res.is_ok())
        service.membership_repo.delete_membership.assert_awaited_once()
        self.session_manager.session.commit.assert_awaited()

    async def test_get_user_permissions_success(self):
        """Get user permissions should return current permission list."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._get_member_permissions = AsyncMock(
            return_value=Ok(["project.settings.read"])
        )

        # Act
        res = await service.get_user_permissions("proj-1", "u2")

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().permissions, ["project.settings.read"])

    async def test_update_user_permissions_invalid_permission(self):
        """Unknown permission values must be rejected."""
        # Arrange
        service = self._make_service()

        # Act
        res = await service.update_user_permissions(
            "proj-1", "actor", "target", ["bogus.permission"]
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, InvalidProjectPermissionError)

    async def test_update_user_permissions_owner_required_for_rw_grant(self):
        """Only project owner can grant users.permissions.read_write."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._get_member_permissions = AsyncMock(
            return_value=Ok(["project.users.permissions.read_write"])
        )
        service.membership_repo.get_membership = AsyncMock(
            return_value=SimpleNamespace(permissions=[])
        )

        # Act
        res = await service.update_user_permissions(
            "proj-1",
            "actor",
            "target",
            ["project.users.permissions.read_write"],
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, OwnerRequiredForGrantError)

    async def test_update_user_permissions_target_not_in_project(self):
        """Updating permissions should fail if target is not a project member."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._get_member_permissions = AsyncMock(
            return_value=Ok(["project.owner"])
        )
        service.membership_repo.get_membership = AsyncMock(return_value=None)

        # Act
        res = await service.update_user_permissions(
            "proj-1", "actor", "target", ["project.settings.read"]
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, UserNotInProjectError)

    async def test_update_user_permissions_success(self):
        """Valid permission update should persist and return updated set."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._get_member_permissions = AsyncMock(
            return_value=Ok(["project.owner"])
        )
        service.membership_repo.get_membership = AsyncMock(
            return_value=SimpleNamespace(permissions=["project.settings.read"])
        )
        service.membership_repo.upsert_membership = AsyncMock(
            return_value=SimpleNamespace()
        )

        # Act
        res = await service.update_user_permissions(
            "proj-1",
            "actor",
            "target",
            ["project.settings.write"],
        )

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().permissions, ["project.settings.write"])
        service.membership_repo.upsert_membership.assert_awaited_once()

    async def test_list_project_users_success_with_filter_and_paging(self):
        """User listing should intersect org members with project members."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service.membership_repo.list_members = AsyncMock(
            return_value=[
                SimpleNamespace(user_id="u1"),
                SimpleNamespace(user_id="u2"),
            ]
        )
        service.kc.get_org_members = AsyncMock(
            return_value=Ok(
                [
                    {"id": "u1", "username": "one", "email": "1@test"},
                    {"id": "u2", "username": "two", "email": "2@test"},
                    {"id": "u3", "username": "three", "email": "3@test"},
                ]
            )
        )

        # Act
        res = await service.list_project_users(
            "proj-1", offset=1, limit=1, q="o"
        )

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().total, 2)
        self.assertEqual(len(res.unwrap().results), 1)
        self.assertEqual(res.unwrap().results[0].id, "u2")

    async def test_authorize_project_permission_archived_project_denied(self):
        """Archived project should reject permission-based access."""
        # Arrange
        service = self._make_service()
        archived_info = SimpleNamespace(archived=True)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((1, "org-1", archived_info))
        )

        # Act
        result = await service.authorize_project_permission(
            "project-uuid",
            "u1",
            ProjectPermission.USERS_GET_ALL,
        )

        # Assert
        self.assertTrue(result.is_err())
        self.assertIsInstance(result.error, ProjectArchivedError)

    async def test_authorize_project_permission_archived_allowed_for_unarchive_flow(
        self,
    ):
        """Archived project auth should pass only when allow_archived is enabled."""
        # Arrange
        service = self._make_service()
        archived_info = SimpleNamespace(archived=True)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((1, "org-1", archived_info))
        )
        service._get_member_permissions = AsyncMock(
            return_value=Ok([ProjectPermission.OWNER.value])
        )

        # Act
        result = await service.authorize_project_permission(
            "project-uuid",
            "u1",
            ProjectPermission.OWNER,
            allow_archived=True,
        )

        # Assert
        self.assertTrue(result.is_ok())

    async def test_update_user_permissions_archived_project_denied(self):
        """Archived project should reject permission updates."""
        # Arrange
        service = self._make_service()
        archived_info = SimpleNamespace(archived=True)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((10, "org-1", archived_info))
        )

        # Act
        res = await service.update_user_permissions(
            "proj-1", "actor", "target", ["project.settings.read"]
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, ProjectArchivedError)

    async def test_set_project_archived_success_not_found_and_state_transitions(
        self,
    ):
        """Archive setter should support success and guard failure branches."""
        # Arrange
        service = self._make_service()
        service.project_repo.get_by_uuid = AsyncMock(return_value=None)

        # Act
        not_found = await service.set_project_archived("missing", True)

        # Assert
        self.assertTrue(not_found.is_err())
        self.assertIsInstance(not_found.error, ProjectNotFoundError)

        # Arrange
        service.project_repo.get_by_uuid = AsyncMock(
            return_value=SimpleNamespace(
                uuid="p1",
                is_archived=False,
            )
        )

        # Act
        ok_res = await service.set_project_archived("p1", True)

        # Assert
        self.assertTrue(ok_res.is_ok())
        self.assertTrue(ok_res.unwrap().archived)

        # Arrange
        service.project_repo.get_by_uuid = AsyncMock(
            return_value=SimpleNamespace(
                uuid="p1",
                is_archived=True,
            )
        )

        # Act
        archived_res = await service.set_project_archived("p1", False)

        # Assert
        self.assertTrue(archived_res.is_ok())
        self.assertFalse(archived_res.unwrap().archived)

        # Arrange
        service.project_repo.get_by_uuid = AsyncMock(
            return_value=SimpleNamespace(
                uuid="p1",
                is_archived=True,
            )
        )

        # Act
        already_archived = await service.set_project_archived("p1", True)

        # Assert
        self.assertTrue(already_archived.is_err())
        self.assertIsInstance(already_archived.error, ProjectArchivedError)


if __name__ == "__main__":
    unittest.main()
