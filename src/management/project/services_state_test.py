"""Category tests for project service unit rules."""

from .services_test_support import (
    PROJECT_PERMISSIONS_ATTR,
    Ok,
    Err,
    AsyncMock,
    SimpleNamespace,
    ProjectPermission,
    ProjectArchivedError,
    ProjectNotFoundError,
    BaseProjectServiceTest,
    InsufficientProjectPermissionError,
    _DummyError,
    encode_project_permission,
)


class TestProjectServiceState(BaseProjectServiceTest):
    """Project service tests grouped by category."""

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

    async def test_list_project_users_propagates_org_member_lookup_error(self):
        """Project user listing should return upstream org-member lookup errors."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service.membership_repo.list_members = AsyncMock(
            return_value=[SimpleNamespace(user_id="u1")]
        )
        service.kc.get_org_members = AsyncMock(
            return_value=Err(_DummyError("kc list failed"))
        )

        # Act
        res = await service.list_project_users("proj-1")

        # Assert
        self.assertTrue(res.is_err())

    async def test_list_project_users_archived_project_denied(self):
        """Archived project should reject user listing."""
        # Arrange
        service = self._make_service()
        archived_info = SimpleNamespace(archived=True)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((10, "org-1", archived_info))
        )

        # Act
        res = await service.list_project_users("proj-1")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, ProjectArchivedError)

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

    async def test_misc_project_error_propagation_paths(self):
        """Project service should propagate upstream collaborator errors on edge paths."""
        # Arrange
        service = self._make_service()

        # _ensure_user_in_org / _get_project_or_err / _get_permissions_from_attrs
        service.kc.get_member_organizations = AsyncMock(
            return_value=Err(_DummyError("org lookup failed"))
        )
        self.assertTrue(
            (await service._ensure_user_in_org("u1", "org-1")).is_err()
        )

        service.project_repo.get_by_uuid = AsyncMock(return_value=None)
        self.assertTrue((await service._get_project_or_err("missing")).is_err())

        service.kc.get_user_attributes = AsyncMock(
            return_value=Err(_DummyError("attr failed"))
        )
        self.assertTrue(
            (await service._get_permissions_from_attrs("u1", "proj-1")).is_err()
        )

        # _set_project_permissions string/non-list branches and attr error
        service.kc.get_user_attributes = AsyncMock(
            side_effect=[
                Err(_DummyError("get attrs failed")),
                Ok({PROJECT_PERMISSIONS_ATTR: "proj-1:project.owner"}),
                Ok({PROJECT_PERMISSIONS_ATTR: {"bad": "shape"}}),
            ]
        )
        service.kc.set_user_attribute = AsyncMock(return_value=Ok(True))
        self.assertTrue(
            (
                await service._set_project_permissions("u1", "proj-1", [])
            ).is_err()
        )
        self.assertTrue(
            (await service._set_project_permissions("u1", "proj-1", [])).is_ok()
        )
        self.assertTrue(
            (
                await service._set_project_permissions(
                    "u1", "proj-1", ["project.settings.read"]
                )
            ).is_ok()
        )

        # _get_member_permissions / _count_project_owners / authorize_project_permission
        service.membership_repo.get_membership = AsyncMock(return_value=None)
        self.assertTrue(
            (await service._get_member_permissions(10, "proj-1", "u1")).is_err()
        )

        service.membership_repo.list_members = AsyncMock(
            return_value=[SimpleNamespace(user_id="u1")]
        )
        service._get_permissions_from_attrs = AsyncMock(
            return_value=Err(_DummyError("count failed"))
        )
        self.assertTrue(
            (await service._count_project_owners(10, "proj-1")).is_err()
        )

        service._get_project_or_err = AsyncMock(
            return_value=Err(_DummyError("project failed"))
        )
        self.assertTrue(
            (
                await service.authorize_project_permission(
                    "proj-1", "u1", ProjectPermission.USERS_GET_ALL
                )
            ).is_err()
        )

        active_info = SimpleNamespace(archived=False)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((1, "org-1", active_info))
        )
        service._get_member_permissions = AsyncMock(
            return_value=Err(_DummyError("member perm failed"))
        )
        self.assertTrue(
            (
                await service.authorize_project_permission(
                    "proj-1", "u1", ProjectPermission.USERS_GET_ALL
                )
            ).is_err()
        )

        # _has_org_wide_project_permission / list_org_projects
        service.project_repo.list_by_member = AsyncMock(
            return_value=[SimpleNamespace(uuid="proj-1")]
        )
        service._get_permissions_from_attrs = AsyncMock(
            return_value=Err(_DummyError("org wide failed"))
        )
        self.assertTrue(
            (
                await service._has_org_wide_project_permission(
                    "u1", "org-1", ProjectPermission.PROJECTS_CREATE
                )
            ).is_err()
        )

        service._has_org_wide_project_permission = AsyncMock(
            return_value=Err(_DummyError("authz failed"))
        )
        self.assertTrue(
            (await service.list_org_projects("u1", "org-1")).is_err()
        )

        # create/list/add/remove/get/update not-found or downstream write errors
        service._get_project_or_err = AsyncMock(
            return_value=Err(_DummyError("project failed"))
        )
        self.assertTrue((await service.list_project_users("proj-1")).is_err())
        self.assertTrue(
            (await service.add_user_to_project("proj-1", "u2")).is_err()
        )
        self.assertTrue(
            (await service.remove_user_from_project("proj-1", "u2")).is_err()
        )
        self.assertTrue(
            (await service.get_user_permissions("proj-1", "u2")).is_err()
        )
        self.assertTrue(
            (
                await service.update_user_permissions(
                    "proj-1", "actor", "target", ["project.settings.read"]
                )
            ).is_err()
        )

        # add/remove/update downstream write failures
        service._get_project_or_err = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._ensure_user_in_org = AsyncMock(return_value=Ok(None))
        service.membership_repo.get_membership = AsyncMock(return_value=None)
        service.membership_repo.upsert_membership = AsyncMock(
            return_value=SimpleNamespace()
        )
        service.kc.get_user_attributes = AsyncMock(
            return_value=Err(_DummyError("set attrs failed"))
        )
        self.assertTrue(
            (await service.add_user_to_project("proj-1", "u2")).is_err()
        )

        service.membership_repo.get_membership = AsyncMock(
            return_value=SimpleNamespace(user_id="u2")
        )
        service._get_permissions_from_attrs = AsyncMock(return_value=Ok([]))
        service.membership_repo.delete_membership = AsyncMock(return_value=True)
        self.assertTrue(
            (await service.remove_user_from_project("proj-1", "u2")).is_err()
        )

        service._get_member_permissions = AsyncMock(
            return_value=Err(_DummyError("actor perms failed"))
        )
        self.assertTrue(
            (
                await service.update_user_permissions(
                    "proj-1", "actor", "target", ["project.settings.read"]
                )
            ).is_err()
        )

        service._get_member_permissions = AsyncMock(
            return_value=Ok(["project.owner"])
        )
        service.membership_repo.get_membership = AsyncMock(
            return_value=SimpleNamespace(user_id="target")
        )
        service._get_permissions_from_attrs = AsyncMock(
            return_value=Err(_DummyError("target perms failed"))
        )
        self.assertTrue(
            (
                await service.update_user_permissions(
                    "proj-1", "actor", "target", ["project.settings.read"]
                )
            ).is_err()
        )

        service._get_permissions_from_attrs = AsyncMock(
            return_value=Ok(["project.owner"])
        )
        service._count_project_owners = AsyncMock(
            return_value=Err(_DummyError("count failed"))
        )
        self.assertTrue(
            (
                await service.update_user_permissions(
                    "proj-1", "actor", "target", []
                )
            ).is_err()
        )

        service._get_permissions_from_attrs = AsyncMock(return_value=Ok([]))
        service.kc.get_user_attributes = AsyncMock(
            return_value=Err(_DummyError("write failed"))
        )
        self.assertTrue(
            (
                await service.update_user_permissions(
                    "proj-1", "actor", "target", ["project.settings.read"]
                )
            ).is_err()
        )
