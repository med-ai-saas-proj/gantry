import os
import unittest
from unittest.mock import Mock, AsyncMock

from pyrusult import Ok, Err


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

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
        service.authorizeProjectPermission = AsyncMock(return_value=Ok(True))
        dependency = requiredProjectPermission(
            ProjectPermission.USERS_GET_ALL,
            allow_archived=True,
        )

        user_info = {"id": "u1", "roles": []}
        result = await dependency("proj-1", user_info, service)

        self.assertEqual(result, user_info)
        service.authorizeProjectPermission.assert_awaited_once_with(
            project_uuid="proj-1",
            user_id="u1",
            required=ProjectPermission.USERS_GET_ALL,
            allow_archived=True,
        )

    async def test_required_project_permission_propagates_error(self):
        service = Mock()
        service.authorizeProjectPermission = AsyncMock(
            return_value=Err(_DummyError("denied"))
        )
        dependency = requiredProjectPermission(ProjectPermission.OWNER)

        with self.assertRaises(_DummyError):
            await dependency("proj-1", {"id": "u1", "roles": []}, service)

    async def test_user_has_role_checks_all_permissions_in_order(self):
        service = Mock()
        service.authorizeProjectPermission = AsyncMock(return_value=Ok(True))
        dependency = userHasRole(
            [
                ProjectPermission.USERS_GET_ALL,
                ProjectPermission.USERS_REMOVE,
            ]
        )

        user_info = {"id": "u1", "roles": []}
        result = await dependency("proj-1", user_info, service)

        self.assertEqual(result, user_info)
        self.assertEqual(
            service.authorizeProjectPermission.await_count,
            2,
        )
