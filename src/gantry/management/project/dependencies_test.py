import os
import unittest
from uuid import UUID
from unittest.mock import Mock, AsyncMock

from pyrusult import Ok


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.management.project.services import (
    ProjectArchivedError,
    InsufficientProjectPermissionError,
)
from gantry.management.project.permissions import ProjectPermission
from gantry.management.project.dependencies import (
    userHasRole,
    requiredProjectPermission,
)


class _DummyError(Exception):
    pass


class TestProjectDependencies(unittest.IsolatedAsyncioTestCase):
    async def test_required_project_permission_authorizes_and_returns_user(
        self,
    ):
        service = Mock()
        service.isProjectArchived = AsyncMock(return_value=Ok(False))
        dependency = requiredProjectPermission(
            ProjectPermission.USERS_GET_ALL,
            allow_archived=True,
        )

        project_uuid = UUID("00000000-0000-0000-0000-000000000001")
        user_info = {
            "id": "u1",
            "roles": [],
            "org_permissions": [],
            "project_permissions": {
                str(project_uuid): [ProjectPermission.USERS_GET_ALL.value]
            },
        }
        result = await dependency(user_info, service, project_uuid)

        self.assertEqual(result["id"], user_info["id"])
        self.assertEqual(result["project_uuid"], project_uuid)
        service.isProjectArchived.assert_awaited_once_with(str(project_uuid))

    async def test_required_project_permission_propagates_error(self):
        service = Mock()
        service.isProjectArchived = AsyncMock(return_value=Ok(False))
        dependency = requiredProjectPermission(ProjectPermission.OWNER)
        project_uuid = UUID("00000000-0000-0000-0000-000000000001")

        with self.assertRaises(InsufficientProjectPermissionError):
            await dependency(
                {
                    "id": "u1",
                    "roles": [],
                    "org_permissions": [],
                    "project_permissions": {str(project_uuid): []},
                },
                service,
                project_uuid,
            )

    async def test_user_has_role_checks_all_permissions_in_order(self):
        service = Mock()
        service.isProjectArchived = AsyncMock(return_value=Ok(False))
        dependency = userHasRole(
            [
                ProjectPermission.USERS_GET_ALL,
                ProjectPermission.USERS_REMOVE,
            ]
        )

        project_uuid = UUID("00000000-0000-0000-0000-000000000001")
        user_info = {
            "id": "u1",
            "roles": [],
            "org_permissions": [],
            "project_permissions": {
                str(project_uuid): [
                    ProjectPermission.USERS_GET_ALL.value,
                    ProjectPermission.USERS_REMOVE.value,
                ]
            },
        }
        result = await dependency(user_info, service, project_uuid)

        self.assertEqual(result["id"], user_info["id"])
        self.assertEqual(result["project_uuid"], project_uuid)

    async def test_required_project_permission_blocks_archived_project(self):
        service = Mock()
        service.isProjectArchived = AsyncMock(return_value=Ok(True))
        dependency = requiredProjectPermission(ProjectPermission.OWNER)

        project_uuid = UUID("00000000-0000-0000-0000-000000000001")
        with self.assertRaises(ProjectArchivedError):
            await dependency(
                {
                    "id": "u1",
                    "roles": [],
                    "org_permissions": [],
                    "project_permissions": {
                        str(project_uuid): [ProjectPermission.OWNER.value]
                    },
                },
                service,
                project_uuid,
            )

    async def test_required_project_permission_allows_archived_when_configured(
        self,
    ):
        service = Mock()
        service.isProjectArchived = AsyncMock(return_value=Ok(True))
        dependency = requiredProjectPermission(
            ProjectPermission.OWNER,
            allow_archived=True,
        )

        project_uuid = UUID("00000000-0000-0000-0000-000000000001")
        result = await dependency(
            {
                "id": "u1",
                "roles": [],
                "org_permissions": [],
                "project_permissions": {
                    str(project_uuid): [ProjectPermission.OWNER.value]
                },
            },
            service,
            project_uuid,
        )

        self.assertEqual(result["project_uuid"], project_uuid)
