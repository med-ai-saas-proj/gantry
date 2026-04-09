from src.management.project import routes
from src.management.project.dtos import (
    PaginationQuery,
    ProjectListQuery,
    CreateProjectRequest,
    UpdateProjectRequest,
    AddProjectUserRequest,
    ProjectUserPermissionsRequest,
)
from src.management.project.permissions import (
    ALL_PERMISSIONS,
)

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock

from pyrusult import Ok


class TestProjectRoutes(unittest.IsolatedAsyncioTestCase):
    async def test_list_and_create_routes(self):
        service = Mock()
        service.listOrgProjects = AsyncMock(return_value=Ok("org-projects"))
        service.listUserProjects = AsyncMock(return_value=Ok("user-projects"))
        service.createProject = AsyncMock(return_value=Ok("created"))
        service.updateProject = AsyncMock(return_value=Ok("updated"))

        self.assertEqual(
            (await routes.list_project_permissions()).permissions,
            ALL_PERMISSIONS,
        )
        self.assertEqual(
            await routes.get_projects(
                {"id": "u1", "roles": []},
                ProjectListQuery(organization="org-1"),
                service,
            ),
            "org-projects",
        )
        self.assertEqual(
            await routes.get_projects(
                {"id": "u1", "roles": []},
                ProjectListQuery(),
                service,
            ),
            "user-projects",
        )
        self.assertEqual(
            await routes.create_project(
                {"id": "u1", "roles": []},
                "org-1",
                CreateProjectRequest(name="P1", description="desc"),
                service,
            ),
            "created",
        )
        self.assertEqual(
            await routes.update_project(
                {"id": "u1", "roles": []},
                "proj-1",
                UpdateProjectRequest(name="P2", description="desc2"),
                service,
            ),
            "updated",
        )

    async def test_membership_and_permission_routes(self):
        service = Mock()
        service.listProjectUsers = AsyncMock(return_value=Ok("users"))
        service.addUserToProject = AsyncMock(return_value=Ok(True))
        service.removeUserFromProject = AsyncMock(return_value=Ok(True))
        service.authorizeProjectPermission = AsyncMock(return_value=Ok(True))
        service.getUserPermissions = AsyncMock(return_value=Ok("perms"))
        service.updateUserPermissions = AsyncMock(return_value=Ok("updated"))

        self.assertEqual(
            await routes.get_project_users(
                {"id": "u1", "roles": []},
                "proj-1",
                PaginationQuery(limit=5, offset=2, q="abc"),
                service,
            ),
            "users",
        )

        add_response = await routes.add_project_user(
            {"id": "u1", "roles": []},
            "proj-1",
            AddProjectUserRequest(user_id="u2"),
            service,
        )
        self.assertEqual(add_response.status_code, 200)

        remove_response = await routes.remove_project_user(
            {"id": "u1", "roles": []},
            "proj-1",
            "u2",
            service,
        )
        self.assertEqual(remove_response.status_code, 200)

        self.assertEqual(
            await routes.get_project_user_permissions(
                {"id": "u1", "roles": []},
                "proj-1",
                "u1",
                service,
            ),
            "perms",
        )
        self.assertEqual(
            await routes.get_project_user_permissions(
                {"id": "actor", "roles": []},
                "proj-1",
                "target",
                service,
            ),
            "perms",
        )
        self.assertEqual(
            await routes.update_project_user_permissions(
                {"id": "actor", "roles": []},
                "proj-1",
                "target",
                ProjectUserPermissionsRequest(
                    permissions=["project.settings.read"]
                ),
                service,
            ),
            "updated",
        )

    async def test_archive_routes(self):
        service = Mock()
        archive_res = SimpleNamespace(project_id="proj-1", archived=True)
        unarchive_res = SimpleNamespace(project_id="proj-1", archived=False)
        service.setProjectArchived = AsyncMock(
            side_effect=[Ok(archive_res), Ok(unarchive_res)]
        )

        self.assertEqual(
            await routes.archive_project(
                {"id": "u1", "roles": []},
                "proj-1",
                service,
            ),
            archive_res,
        )
        self.assertEqual(
            await routes.unarchive_project(
                {"id": "u1", "roles": []},
                "proj-1",
                service,
            ),
            unarchive_res,
        )
