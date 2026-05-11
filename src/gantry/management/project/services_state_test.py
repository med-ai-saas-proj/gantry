"""Category tests for project service unit rules."""

from .services_test_support import (
    PROJECT_PERMISSIONS_ATTR,
    Ok,
    Err,
    AsyncMock,
    ResultStatus,
    SimpleNamespace,
    ProjectPermission,
    ProjectArchivedError,
    ProjectNotFoundError,
    BaseProjectServiceTest,
    InsufficientProjectPermissionError,
    _DummyError,
)


class TestProjectServiceState(BaseProjectServiceTest):
    """Project service tests grouped by category."""

    async def test_list_project_users_success_with_filter_and_paging(self):
        """User listing should intersect org members with project members."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service.membership_repo.listMembers = AsyncMock(
            return_value=[
                SimpleNamespace(user_id="u1"),
                SimpleNamespace(user_id="u2"),
            ]
        )
        service.kc.getOrgMembers = AsyncMock(
            return_value=Ok(
                [
                    {"id": "u1", "username": "one", "email": "1@test"},
                    {"id": "u2", "username": "two", "email": "2@test"},
                    {"id": "u3", "username": "three", "email": "3@test"},
                ]
            )
        )

        # Act
        res = await service.listProjectUsers("proj-1", offset=1, limit=1, q="o")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().total, 2)
        self.assertEqual(len(res.unwrap().results), 1)
        self.assertEqual(res.unwrap().results[0].id, "u2")

    async def test_get_project_settings_creates_missing_row(self):
        service = self._make_service()
        service._getProjectOrErr = AsyncMock(
            return_value=Ok(
                (
                    10,
                    "org-1",
                    SimpleNamespace(archived=False),
                )
            )
        )
        service.settings_repo.getOrCreate = AsyncMock(
            return_value=SimpleNamespace(
                rate_limit=120,
                spending_limit=6000,
                extra={"burst": True},
            )
        )

        res = await service.getProjectSettings("proj-1")

        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().rate_limit, 120)
        self.assertEqual(res.unwrap().spending_limit, 6000)
        self.assertEqual(res.unwrap().extra, {"burst": True})

    async def test_update_project_settings_flattens_extra(self):
        service = self._make_service()
        service._getProjectOrErr = AsyncMock(
            return_value=Ok(
                (
                    10,
                    "org-1",
                    SimpleNamespace(archived=False),
                )
            )
        )
        service.settings_repo.upsert = AsyncMock(
            return_value=SimpleNamespace(
                rate_limit=90,
                spending_limit=7000,
                extra={"ui.theme": "dark"},
            )
        )

        res = await service.updateProjectSettings(
            "proj-1",
            90,
            7000,
            {"ui": {"theme": "dark"}},
        )

        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().spending_limit, 7000)
        self.assertEqual(res.unwrap().extra, {"ui.theme": "dark"})
        service.settings_repo.upsert.assert_awaited_once()

    async def test_get_project_settings_returns_none_for_missing_limits(self):
        service = self._make_service()
        service._getProjectOrErr = AsyncMock(
            return_value=Ok(
                (
                    10,
                    "org-1",
                    SimpleNamespace(archived=False),
                )
            )
        )
        service.settings_repo.getOrCreate = AsyncMock(
            return_value=SimpleNamespace(
                rate_limit=None,
                spending_limit=None,
                extra={},
            )
        )

        res = await service.getProjectSettings("proj-1")

        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertIsNone(res.unwrap().rate_limit)
        self.assertIsNone(res.unwrap().spending_limit)

    async def test_update_project_settings_returns_none_for_missing_limits(
        self,
    ):
        service = self._make_service()
        service._getProjectOrErr = AsyncMock(
            return_value=Ok(
                (
                    10,
                    "org-1",
                    SimpleNamespace(archived=False),
                )
            )
        )
        service.settings_repo.upsert = AsyncMock(
            return_value=SimpleNamespace(
                rate_limit=None,
                spending_limit=None,
                extra={"burst": False},
            )
        )

        res = await service.updateProjectSettings(
            "proj-1",
            None,
            None,
            {"burst": False},
        )

        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertIsNone(res.unwrap().rate_limit)
        self.assertIsNone(res.unwrap().spending_limit)

    async def test_list_project_users_propagates_org_member_lookup_error(self):
        """Project user listing should return upstream org-member lookup errors."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service.membership_repo.listMembers = AsyncMock(
            return_value=[SimpleNamespace(user_id="u1")]
        )
        service.kc.getOrgMembers = AsyncMock(
            return_value=Err(_DummyError("kc list failed"))
        )

        # Act
        res = await service.listProjectUsers("proj-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)

    async def test_list_project_users_archived_project_denied(self):
        """Archived project should reject user listing."""
        # Arrange
        service = self._make_service()
        archived_info = SimpleNamespace(archived=True)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", archived_info))
        )

        # Act
        res = await service.listProjectUsers("proj-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), ProjectArchivedError)

    async def test_authorize_project_permission_archived_project_denied(self):
        """Archived project should reject permission-based access."""
        # Arrange
        service = self._make_service()
        archived_info = SimpleNamespace(archived=True)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((1, "org-1", archived_info))
        )

        # Act
        result = await service.authorizeProjectPermission(
            "project-uuid",
            "u1",
            ProjectPermission.USERS_GET_ALL,
        )

        # Assert
        self.assertTrue(result.status == ResultStatus.Err)
        self.assertIsInstance(result.err(), ProjectArchivedError)

    async def test_authorize_project_permission_archived_allowed_for_unarchive_flow(
        self,
    ):
        """Archived project auth should pass only when allow_archived is enabled."""
        # Arrange
        service = self._make_service()
        archived_info = SimpleNamespace(archived=True)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((1, "org-1", archived_info))
        )
        service._getMemberPermissions = AsyncMock(
            return_value=Ok([ProjectPermission.OWNER.value])
        )

        # Act
        result = await service.authorizeProjectPermission(
            "project-uuid",
            "u1",
            ProjectPermission.OWNER,
            allow_archived=True,
        )

        # Assert
        self.assertTrue(result.status == ResultStatus.Ok)

    async def test_set_project_archived_success_not_found_and_state_transitions(
        self,
    ):
        """Archive setter should support success and guard failure branches."""
        # Arrange
        service = self._make_service()
        service.project_repo.getByUuid = AsyncMock(return_value=None)

        # Act
        not_found = await service.setProjectArchived("missing", True)

        # Assert
        self.assertTrue(not_found.status == ResultStatus.Err)
        self.assertIsInstance(not_found.err(), ProjectNotFoundError)

        # Arrange
        service.project_repo.getByUuid = AsyncMock(
            return_value=SimpleNamespace(
                uuid="p1",
                is_archived=False,
            )
        )

        # Act
        ok_res = await service.setProjectArchived("p1", True)

        # Assert
        self.assertTrue(ok_res.status == ResultStatus.Ok)
        self.assertTrue(ok_res.unwrap().archived)

        # Arrange
        service.project_repo.getByUuid = AsyncMock(
            return_value=SimpleNamespace(
                uuid="p1",
                is_archived=True,
            )
        )

        # Act
        archived_res = await service.setProjectArchived("p1", False)

        # Assert
        self.assertTrue(archived_res.status == ResultStatus.Ok)
        self.assertFalse(archived_res.unwrap().archived)

        # Arrange
        service.project_repo.getByUuid = AsyncMock(
            return_value=SimpleNamespace(
                uuid="p1",
                is_archived=True,
            )
        )

        # Act
        already_archived = await service.setProjectArchived("p1", True)

        # Assert
        self.assertTrue(already_archived.status == ResultStatus.Err)
        self.assertIsInstance(already_archived.err(), ProjectArchivedError)

    async def test_misc_project_error_propagation_paths(self):
        """Project service should propagate upstream collaborator errors on edge paths."""
        # Arrange
        service = self._make_service()

        # _ensure_user_in_org / _get_project_or_err / _get_permissions_from_attrs
        service.kc.getMemberOrganizations = AsyncMock(
            return_value=Err(_DummyError("org lookup failed"))
        )
        self.assertTrue(
            (await service._ensureUserInOrg("u1", "org-1")).status
            == ResultStatus.Err
        )

        service.project_repo.getSnapshotByUuid = AsyncMock(return_value=None)
        self.assertTrue(
            (await service._getProjectOrErr("missing")).status
            == ResultStatus.Err
        )

        service.kc.getUserAttributes = AsyncMock(
            return_value=Err(_DummyError("attr failed"))
        )
        self.assertTrue(
            (await service._getPermissionsFromAttrs("u1", "proj-1")).status
            == ResultStatus.Err
        )

        # _set_project_permissions attr error and invalid-shape branches
        service.kc.getUserAttributes = AsyncMock(
            side_effect=[
                Err(_DummyError("get attrs failed")),
                Ok({PROJECT_PERMISSIONS_ATTR: "not-a-project-map"}),
                Ok({PROJECT_PERMISSIONS_ATTR: {"bad": None}}),
            ]
        )
        service.kc.setUserAttribute = AsyncMock(return_value=Ok(True))
        self.assertTrue(
            (await service._setProjectPermissions("u1", "proj-1", [])).status
            == ResultStatus.Err
        )
        self.assertTrue(
            (await service._setProjectPermissions("u1", "proj-1", [])).status
            == ResultStatus.Ok
        )
        self.assertTrue(
            (
                await service._setProjectPermissions(
                    "u1", "proj-1", ["project.settings.read"]
                )
            ).status
            == ResultStatus.Ok
        )
        service.kc.setUserAttribute.assert_awaited_with(
            "u1",
            PROJECT_PERMISSIONS_ATTR,
            {"proj-1": ["project.settings.read"]},
        )

        # _get_member_permissions / _count_project_owners / authorize_project_permission
        service.membership_repo.getMembership = AsyncMock(return_value=None)
        self.assertTrue(
            (await service._getMemberPermissions(10, "proj-1", "u1")).status
            == ResultStatus.Err
        )

        service.membership_repo.listMembers = AsyncMock(
            return_value=[SimpleNamespace(user_id="u1")]
        )
        service._getPermissionsFromAttrs = AsyncMock(
            return_value=Err(_DummyError("count failed"))
        )
        self.assertTrue(
            (await service._countProjectOwners(10, "proj-1")).status
            == ResultStatus.Err
        )

        service._getProjectOrErr = AsyncMock(
            return_value=Err(_DummyError("project failed"))
        )
        self.assertTrue(
            (
                await service.authorizeProjectPermission(
                    "proj-1", "u1", ProjectPermission.USERS_GET_ALL
                )
            ).status
            == ResultStatus.Err
        )

        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((1, "org-1", active_info))
        )
        service._getMemberPermissions = AsyncMock(
            return_value=Err(_DummyError("member perm failed"))
        )
        self.assertTrue(
            (
                await service.authorizeProjectPermission(
                    "proj-1", "u1", ProjectPermission.USERS_GET_ALL
                )
            ).status
            == ResultStatus.Err
        )

        # _has_org_wide_project_permission / list_org_projects
        service.project_repo.listByMember = AsyncMock(
            return_value=[SimpleNamespace(uuid="proj-1")]
        )
        service._getPermissionsFromAttrs = AsyncMock(
            return_value=Err(_DummyError("org wide failed"))
        )
        self.assertTrue(
            (
                await service._hasOrgWideProjectPermission(
                    "u1", "org-1", ProjectPermission.SETTINGS_READ
                )
            ).status
            == ResultStatus.Err
        )

        service.project_repo.listByOrg = AsyncMock(return_value=[])
        self.assertTrue(
            (await service.listOrgProjects("u1", "org-1")).status
            == ResultStatus.Ok
        )

        # create/list/add/remove/get/update not-found or downstream write errors
        service._getProjectOrErr = AsyncMock(
            return_value=Err(_DummyError("project failed"))
        )
        self.assertTrue(
            (await service.listProjectUsers("proj-1")).status
            == ResultStatus.Err
        )
        self.assertTrue(
            (await service.addUserToProject("proj-1", "u2")).status
            == ResultStatus.Err
        )
        self.assertTrue(
            (await service.removeUserFromProject("proj-1", "u2")).status
            == ResultStatus.Err
        )
        self.assertTrue(
            (await service.getUserPermissions("proj-1", "u2")).status
            == ResultStatus.Err
        )
        self.assertTrue(
            (
                await service.updateUserPermissions(
                    "proj-1", "actor", "target", ["project.settings.read"]
                )
            ).status
            == ResultStatus.Err
        )

        # add/remove/update downstream write failures
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._ensureUserInOrg = AsyncMock(return_value=Ok(None))
        service.membership_repo.getMembership = AsyncMock(return_value=None)
        service.membership_repo.upsertMembership = AsyncMock(
            return_value=SimpleNamespace()
        )
        service.kc.getUserAttributes = AsyncMock(
            return_value=Err(_DummyError("set attrs failed"))
        )
        self.assertTrue(
            (await service.addUserToProject("proj-1", "u2")).status
            == ResultStatus.Err
        )

        service.membership_repo.getMembership = AsyncMock(
            return_value=SimpleNamespace(user_id="u2")
        )
        service._getPermissionsFromAttrs = AsyncMock(return_value=Ok([]))
        service.membership_repo.deleteMembership = AsyncMock(return_value=True)
        self.assertTrue(
            (await service.removeUserFromProject("proj-1", "u2")).status
            == ResultStatus.Err
        )

        service._getMemberPermissions = AsyncMock(
            return_value=Err(_DummyError("actor perms failed"))
        )
        self.assertTrue(
            (
                await service.updateUserPermissions(
                    "proj-1", "actor", "target", ["project.settings.read"]
                )
            ).status
            == ResultStatus.Err
        )

        service._getMemberPermissions = AsyncMock(
            return_value=Ok(["project.owner"])
        )
        service.membership_repo.getMembership = AsyncMock(
            return_value=SimpleNamespace(user_id="target")
        )
        service._getPermissionsFromAttrs = AsyncMock(
            return_value=Err(_DummyError("target perms failed"))
        )
        self.assertTrue(
            (
                await service.updateUserPermissions(
                    "proj-1", "actor", "target", ["project.settings.read"]
                )
            ).status
            == ResultStatus.Err
        )

        service._getPermissionsFromAttrs = AsyncMock(
            return_value=Ok(["project.owner"])
        )
        service._countProjectOwners = AsyncMock(
            return_value=Err(_DummyError("count failed"))
        )
        self.assertTrue(
            (
                await service.updateUserPermissions(
                    "proj-1", "actor", "target", []
                )
            ).status
            == ResultStatus.Err
        )

        service._getPermissionsFromAttrs = AsyncMock(return_value=Ok([]))
        service.kc.getUserAttributes = AsyncMock(
            return_value=Err(_DummyError("write failed"))
        )
        self.assertTrue(
            (
                await service.updateUserPermissions(
                    "proj-1", "actor", "target", ["project.settings.read"]
                )
            ).status
            == ResultStatus.Err
        )
