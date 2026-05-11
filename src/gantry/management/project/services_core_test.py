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
    unittest,
    _DummyError,
)


class TestProjectServiceCore(BaseProjectServiceTest):
    """Project service tests grouped by category."""

    def test_extract_project_permissions_supports_grouped_map(self):
        """Project permission extraction should read grouped attr maps."""
        # Arrange
        service = self._make_service()

        # Act
        from_map = service._extractProjectPermissions(
            {PROJECT_PERMISSIONS_ATTR: {"proj-1": ["project.owner"]}},
            "proj-1",
        )
        from_list = service._extractProjectPermissions(
            {
                PROJECT_PERMISSIONS_ATTR: {
                    "proj-1": [
                        "project.settings.read",
                        "project.settings.read",
                    ],
                    "proj-2": ["project.settings.write"],
                }
            },
            "proj-1",
        )
        from_invalid = service._extractProjectPermissions(
            {PROJECT_PERMISSIONS_ATTR: {"x": "y"}},
            "proj-1",
        )

        # Assert
        self.assertEqual(from_map, ["project.owner"])
        self.assertEqual(from_list, ["project.settings.read"])
        self.assertEqual(from_invalid, [])

    def test_extract_project_permissions_ignores_old_flat_entries(self):
        """Old flat entries should not be accepted by the new contract."""
        # Arrange
        service = self._make_service()

        # Act
        res = service._extractProjectPermissions(
            {PROJECT_PERMISSIONS_ATTR: ["bad-entry", "proj-1:project.owner"]},
            "proj-1",
        )

        # Assert
        self.assertEqual(res, [])

    async def test_get_project_or_err_success(self):
        """Known project uuid should map repository row into DTO tuple."""
        # Arrange
        service = self._make_service()
        service.project_repo.getSnapshotByUuid = AsyncMock(
            return_value=SimpleNamespace(
                id=10,
                uuid="proj-1",
                name="P1",
                description=None,
                organization_id="org-1",
                is_archived=False,
            )
        )

        # Act
        res = await service._getProjectOrErr("proj-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap()[0], 10)

    async def test_set_project_permissions_replaces_only_one_project_slice(
        self,
    ):
        """Updating one project should keep entries from other projects."""
        # Arrange
        service = self._make_service()
        service.kc.getUserAttributes = AsyncMock(
            return_value=Ok(
                {
                    PROJECT_PERMISSIONS_ATTR: {
                        "proj-1": ["project.settings.read"],
                        "proj-2": ["project.owner"],
                    }
                }
            )
        )
        service.kc.setUserAttribute = AsyncMock(return_value=Ok(True))

        # Act
        res = await service._setProjectPermissions(
            "u1",
            "proj-1",
            ["project.users.get_all", "project.settings.write"],
        )

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        service.kc.setUserAttribute.assert_awaited_once_with(
            "u1",
            PROJECT_PERMISSIONS_ATTR,
            {
                "proj-2": ["project.owner"],
                "proj-1": [
                    "project.users.get_all",
                    "project.settings.write",
                ],
            },
        )

    async def test_set_project_permissions_ignores_non_string_entries(self):
        """Project permission writes should ignore malformed non-string entries."""
        # Arrange
        service = self._make_service()
        service.kc.getUserAttributes = AsyncMock(
            return_value=Ok(
                {
                    PROJECT_PERMISSIONS_ATTR: {
                        "proj-2": ["project.owner"],
                        "bad": None,
                    }
                }
            )
        )
        service.kc.setUserAttribute = AsyncMock(return_value=Ok(True))

        # Act
        res = await service._setProjectPermissions("u1", "proj-1", [])

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        service.kc.setUserAttribute.assert_awaited_once_with(
            "u1",
            PROJECT_PERMISSIONS_ATTR,
            {"proj-2": ["project.owner"]},
        )

    async def test_ensure_user_in_org_success_and_not_found(self):
        """Membership lookup should return Ok for matching org else error."""
        # Arrange
        service = self._make_service()
        service.kc.getMemberOrganizations = AsyncMock(
            return_value=Ok([{"id": "org-1"}])
        )

        # Act
        ok_res = await service._ensureUserInOrg("u1", "org-1")

        # Assert
        self.assertTrue(ok_res.status == ResultStatus.Ok)

        # Arrange
        service.kc.getMemberOrganizations = AsyncMock(
            return_value=Ok([{"id": "org-2"}])
        )

        # Act
        err_res = await service._ensureUserInOrg("u1", "org-1")

        # Assert
        self.assertTrue(err_res.status == ResultStatus.Err)

    async def test_get_project_or_err_not_found(self):
        """Unknown project uuid should return project_not_found."""
        # Arrange
        service = self._make_service()
        service.project_repo.getSnapshotByUuid = AsyncMock(return_value=None)

        # Act
        res = await service._getProjectOrErr("missing")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), ProjectNotFoundError)

    def test_ensure_project_active_helper(self):
        """Archived project should be rejected by helper."""
        # Arrange
        service = self._make_service()

        # Act
        ok_res = service._ensureProjectActive(SimpleNamespace(archived=False))
        err_res = service._ensureProjectActive(SimpleNamespace(archived=True))

        # Assert
        self.assertTrue(ok_res.status == ResultStatus.Ok)
        self.assertTrue(err_res.status == ResultStatus.Err)
        self.assertIsInstance(err_res.err(), ProjectArchivedError)

    async def test_authorize_project_permission_denied(self):
        """Authorization should fail when member lacks required permission."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((1, "org-1", active_info))
        )
        service._getMemberPermissions = AsyncMock(return_value=Ok([]))

        # Act
        result = await service.authorizeProjectPermission(
            "project-uuid",
            "u1",
            ProjectPermission.USERS_GET_ALL,
        )

        # Assert
        self.assertTrue(result.status == ResultStatus.Err)
        self.assertIsInstance(result.err(), InsufficientProjectPermissionError)

    async def test_authorize_project_permission_owner_inherits_children(self):
        """Project owner should be authorized for child permissions."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((1, "org-1", active_info))
        )
        service._isOrgOwner = AsyncMock(return_value=Ok(False))
        service._getMemberPermissions = AsyncMock(
            return_value=Ok([ProjectPermission.OWNER.value])
        )

        # Act
        result = await service.authorizeProjectPermission(
            "project-uuid",
            "u1",
            ProjectPermission.USERS_REMOVE,
        )

        # Assert
        self.assertTrue(result.status == ResultStatus.Ok)

    async def test_authorize_project_permission_org_owner_bypasses_membership(
        self,
    ):
        """Organization owner should pass project auth without project membership."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((1, "org-1", active_info))
        )
        service._isOrgOwner = AsyncMock(return_value=Ok(True))
        service._getMemberPermissions = AsyncMock()

        # Act
        result = await service.authorizeProjectPermission(
            "project-uuid",
            "u-org-owner",
            ProjectPermission.USERS_REMOVE,
        )

        # Assert
        self.assertTrue(result.status == ResultStatus.Ok)
        service._getMemberPermissions.assert_not_awaited()

    async def test_project_owner_can_read_other_user_permissions_via_inherited_rw(
        self,
    ):
        """Project owner should read another user's permissions via inherited RW."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((1, "org-1", active_info))
        )
        service._getMemberPermissions = AsyncMock(
            return_value=Ok([ProjectPermission.OWNER.value])
        )

        # Act
        result = await service.authorizeProjectPermission(
            "project-uuid",
            "u-owner",
            ProjectPermission.USERS_PERMISSIONS_RW,
        )

        # Assert
        self.assertTrue(result.status == ResultStatus.Ok)

    async def test_create_project_requires_org_projects_create(self):
        """Create project should fail if actor lacks org-scoped create permission."""
        # Arrange
        service = self._make_service()
        service._getOrgPermissions = AsyncMock(return_value=Ok([]))

        # Act
        res = await service.createProject("u1", "org-1", "p1", None)

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), InsufficientProjectPermissionError)

    async def test_create_project_success_sets_owner_permission_attribute(self):
        """Creating a project should add owner permission in flat attr form."""
        # Arrange
        service = self._make_service()
        service._getOrgPermissions = AsyncMock(
            return_value=Ok(["organization.owner"])
        )
        service.project_repo.create = AsyncMock(
            return_value=SimpleNamespace(
                id=10,
                uuid="proj-1",
                name="p1",
                description=None,
                organization_id="org-1",
                is_archived=False,
            )
        )
        service.membership_repo.upsertMembership = AsyncMock(
            return_value=SimpleNamespace()
        )
        service._setProjectPermissions = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.createProject("u1", "org-1", "p1", None)

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        service._setProjectPermissions.assert_awaited_once_with(
            "u1", "proj-1", ["project.owner"]
        )
        self.session_manager.session.commit.assert_awaited()

    async def test_create_project_fails_when_owner_attr_write_fails(self):
        """Project creation should surface attr-write failure before commit."""
        # Arrange
        service = self._make_service()
        service._getOrgPermissions = AsyncMock(
            return_value=Ok(["organization.owner"])
        )
        service.project_repo.create = AsyncMock(
            return_value=SimpleNamespace(
                id=10,
                uuid="proj-1",
                name="p1",
                description=None,
                organization_id="org-1",
                is_archived=False,
            )
        )
        service.membership_repo.upsertMembership = AsyncMock(
            return_value=SimpleNamespace()
        )
        service._setProjectPermissions = AsyncMock(
            return_value=Err(_DummyError("kc write failed"))
        )

        # Act
        res = await service.createProject("u1", "org-1", "p1", None)

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.session_manager.session.commit.assert_not_awaited()

    async def test_create_project_propagates_org_permission_lookup_error(
        self,
    ):
        """Project creation should return upstream org permission lookup errors."""
        # Arrange
        service = self._make_service()
        service._getOrgPermissions = AsyncMock(
            return_value=Err(_DummyError("kc failed"))
        )

        # Act
        res = await service.createProject("u1", "org-1", "p1", None)

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)

    async def test_update_project_updates_mutable_metadata(self):
        """Update project should persist new name and description."""
        # Arrange
        service = self._make_service()
        service.project_repo.updateByUuid = AsyncMock(
            return_value=SimpleNamespace(
                id=10,
                uuid="proj-1",
                name="New",
                description="new",
                organization_id="org-1",
                is_archived=False,
            )
        )

        # Act
        res = await service.updateProject("proj-1", "New", "new")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().name, "New")
        self.session_manager.session.commit.assert_awaited_once()

    async def test_update_project_rejects_archived_project(self):
        """Archived project updates surface as not found from the repository."""
        # Arrange
        service = self._make_service()
        service.project_repo.updateByUuid = AsyncMock(return_value=None)

        # Act
        res = await service.updateProject("proj-1", "New", "new")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), ProjectNotFoundError)

    async def test_list_user_projects_org_membership_error(self):
        """List by organization should fail if actor not in org."""
        # Arrange
        service = self._make_service()
        service._ensureUserInOrg = AsyncMock(
            return_value=Err(_DummyError("not in org"))
        )

        # Act
        res = await service.listUserProjects("u1", "org-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)

    async def test_list_user_projects_success(self):
        """List user projects should map repository rows to DTO."""
        # Arrange
        service = self._make_service()
        service.project_repo.listByMember = AsyncMock(
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
        res = await service.listUserProjects("u1", None)

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().total, 1)
        self.assertEqual(res.unwrap().results[0].name, "P1")

    async def test_list_user_projects_with_org_filter_checks_membership(self):
        """Org-scoped project listing should validate org membership first."""
        # Arrange
        service = self._make_service()
        service._ensureUserInOrg = AsyncMock(return_value=Ok(None))
        service.project_repo.listByMember = AsyncMock(return_value=[])

        # Act
        res = await service.listUserProjects("u1", "org-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        service._ensureUserInOrg.assert_awaited_once_with("u1", "org-1")

    async def test_list_accessible_projects_uses_org_wide_view_for_org_owner(
        self,
    ):
        """Org owners should see every project in the organization."""
        service = self._make_service()
        service._isOrgOwner = AsyncMock(return_value=Ok(True))
        service.project_repo.listByOrg = AsyncMock(
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

        res = await service.listAccessibleProjects("u1", "org-1")

        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().total, 1)

    async def test_list_accessible_projects_uses_membership_for_non_owner(self):
        """Non-owners should see only projects they joined in the org."""
        service = self._make_service()
        service._isOrgOwner = AsyncMock(return_value=Ok(False))
        service.listUserProjects = AsyncMock(return_value=Ok("joined-projects"))

        res = await service.listAccessibleProjects("u1", "org-1")

        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap(), "joined-projects")
        service.listUserProjects.assert_awaited_once_with("u1", "org-1")

    async def test_has_org_wide_permission_true_and_false(self):
        """Org-wide permission check should respect membership permissions."""
        # Arrange
        service = self._make_service()
        service.project_repo.listByMember = AsyncMock(
            return_value=[
                SimpleNamespace(uuid="proj-1"),
                SimpleNamespace(uuid="proj-2"),
            ]
        )
        service._getPermissionsFromAttrs = AsyncMock(
            side_effect=[
                Ok(["project.settings.read"]),
                Ok(["projects.get_all"]),
            ]
        )

        # Act
        true_res = await service._hasOrgWideProjectPermission(
            "u1", "org-1", ProjectPermission.SETTINGS_READ
        )

        # Assert
        self.assertTrue(true_res.status == ResultStatus.Ok)
        self.assertTrue(true_res.unwrap())

        # Arrange
        service.project_repo.listByMember = AsyncMock(
            return_value=[SimpleNamespace(uuid="proj-1")]
        )
        service._getPermissionsFromAttrs = AsyncMock(
            return_value=Ok(["project.settings.read"])
        )

        # Act
        false_res = await service._hasOrgWideProjectPermission(
            "u1", "org-1", ProjectPermission.SETTINGS_WRITE
        )

        # Assert
        self.assertTrue(false_res.status == ResultStatus.Ok)
        self.assertFalse(false_res.unwrap())

    async def test_has_org_wide_permission_uses_project_uuids_for_each_joined_project(
        self,
    ):
        """Org-wide checks should evaluate every joined project uuid."""
        # Arrange
        service = self._make_service()
        service.project_repo.listByMember = AsyncMock(
            return_value=[
                SimpleNamespace(uuid="proj-a"),
                SimpleNamespace(uuid="proj-b"),
            ]
        )
        service._getPermissionsFromAttrs = AsyncMock(
            side_effect=[
                Ok([]),
                Ok([ProjectPermission.SETTINGS_READ.value]),
            ]
        )

        # Act
        res = await service._hasOrgWideProjectPermission(
            "actor",
            "org-1",
            ProjectPermission.SETTINGS_READ,
        )

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertTrue(res.unwrap())
        self.assertEqual(
            service._getPermissionsFromAttrs.await_args_list,
            [
                unittest.mock.call("actor", "proj-a"),
                unittest.mock.call("actor", "proj-b"),
            ],
        )

    async def test_list_org_projects_success(self):
        """Org project list should return DTO rows from the repository."""
        # Arrange
        service = self._make_service()
        service.project_repo.listByOrg = AsyncMock(
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
        res = await service.listOrgProjects("u1", "org-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().total, 1)

    async def test_get_project_returns_project_for_org_owner(self):
        """Organization owner should read any project in the same org."""
        service = self._make_service()
        project_info = SimpleNamespace(
            project_uuid="proj-1",
            name="P1",
            description=None,
            organization_id="org-1",
            archived=False,
        )
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((1, "org-1", project_info))
        )
        service._isOrgOwner = AsyncMock(return_value=Ok(True))

        res = await service.getProject("proj-1", "u-owner")

        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().project_uuid, "proj-1")

    async def test_get_project_returns_project_for_member(self):
        """Project member should read the project metadata."""
        service = self._make_service()
        project_info = SimpleNamespace(
            project_uuid="proj-1",
            name="P1",
            description=None,
            organization_id="org-1",
            archived=False,
        )
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((1, "org-1", project_info))
        )
        service._isOrgOwner = AsyncMock(return_value=Ok(False))
        service.membership_repo.getMembership = AsyncMock(
            return_value=SimpleNamespace(project_id=1, user_id="u1")
        )

        res = await service.getProject("proj-1", "u1")

        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().project_uuid, "proj-1")

    async def test_get_project_denies_non_member_non_owner(self):
        """Users outside the project should not read project metadata."""
        service = self._make_service()
        project_info = SimpleNamespace(
            project_uuid="proj-1",
            name="P1",
            description=None,
            organization_id="org-1",
            archived=False,
        )
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((1, "org-1", project_info))
        )
        service._isOrgOwner = AsyncMock(return_value=Ok(False))
        service.membership_repo.getMembership = AsyncMock(return_value=None)

        res = await service.getProject("proj-1", "u1")

        self.assertTrue(res.status == ResultStatus.Err)
        self.assertEqual(res.err().code, "user_not_in_project")
