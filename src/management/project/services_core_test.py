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
    unittest,
    _DummyError,
    encode_project_permission,
)


class TestProjectServiceCore(BaseProjectServiceTest):
    """Project service tests grouped by category."""

    def test_extract_project_permissions_supports_string_and_list(self):
        """Project permission extraction should accept string/list values."""
        # Arrange
        service = self._make_service()

        # Act
        from_string = service._extract_project_permissions(
            {
                PROJECT_PERMISSIONS_ATTR: encode_project_permission(
                    "proj-1", "project.owner"
                )
            },
            "proj-1",
        )
        from_list = service._extract_project_permissions(
            {
                PROJECT_PERMISSIONS_ATTR: [
                    encode_project_permission(
                        "proj-1", "project.settings.read"
                    ),
                    123,
                    encode_project_permission(
                        "proj-2", "project.settings.write"
                    ),
                ]
            },
            "proj-1",
        )
        from_invalid = service._extract_project_permissions(
            {PROJECT_PERMISSIONS_ATTR: {"x": "y"}},
            "proj-1",
        )

        # Assert
        self.assertEqual(from_string, ["project.owner"])
        self.assertEqual(from_list, ["project.settings.read"])
        self.assertEqual(from_invalid, [])

    def test_extract_project_permissions_ignores_malformed_entries(self):
        """Malformed flat entries should be ignored during extraction."""
        # Arrange
        service = self._make_service()

        # Act
        res = service._extract_project_permissions(
            {PROJECT_PERMISSIONS_ATTR: ["bad-entry", "proj-1:project.owner"]},
            "proj-1",
        )

        # Assert
        self.assertEqual(res, ["project.owner"])

    async def test_get_project_or_err_success(self):
        """Known project uuid should map repository row into DTO tuple."""
        # Arrange
        service = self._make_service()
        service.project_repo.get_by_uuid = AsyncMock(
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
        res = await service._get_project_or_err("proj-1")

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap()[0], 10)

    async def test_set_project_permissions_replaces_only_one_project_slice(
        self,
    ):
        """Updating one project should keep entries from other projects."""
        # Arrange
        service = self._make_service()
        service.kc.get_user_attributes = AsyncMock(
            return_value=Ok(
                {
                    PROJECT_PERMISSIONS_ATTR: [
                        encode_project_permission(
                            "proj-1", "project.settings.read"
                        ),
                        encode_project_permission("proj-2", "project.owner"),
                        "invalid-entry",
                    ]
                }
            )
        )
        service.kc.set_user_attribute = AsyncMock(return_value=Ok(True))

        # Act
        res = await service._set_project_permissions(
            "u1",
            "proj-1",
            ["project.users.get_all", "project.settings.write"],
        )

        # Assert
        self.assertTrue(res.is_ok())
        service.kc.set_user_attribute.assert_awaited_once_with(
            "u1",
            PROJECT_PERMISSIONS_ATTR,
            [
                encode_project_permission("proj-2", "project.owner"),
                encode_project_permission("proj-1", "project.users.get_all"),
                encode_project_permission("proj-1", "project.settings.write"),
            ],
        )

    async def test_set_project_permissions_ignores_non_string_entries(self):
        """Project permission writes should ignore malformed non-string entries."""
        # Arrange
        service = self._make_service()
        service.kc.get_user_attributes = AsyncMock(
            return_value=Ok(
                {PROJECT_PERMISSIONS_ATTR: [123, None, "proj-2:project.owner"]}
            )
        )
        service.kc.set_user_attribute = AsyncMock(return_value=Ok(True))

        # Act
        res = await service._set_project_permissions("u1", "proj-1", [])

        # Assert
        self.assertTrue(res.is_ok())
        service.kc.set_user_attribute.assert_awaited_once_with(
            "u1",
            PROJECT_PERMISSIONS_ATTR,
            [encode_project_permission("proj-2", "project.owner")],
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

    async def test_authorize_project_permission_owner_inherits_children(self):
        """Project owner should be authorized for child permissions."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((1, "org-1", active_info))
        )
        service._get_member_permissions = AsyncMock(
            return_value=Ok([ProjectPermission.OWNER.value])
        )

        # Act
        result = await service.authorize_project_permission(
            "project-uuid",
            "u1",
            ProjectPermission.USERS_REMOVE,
        )

        # Assert
        self.assertTrue(result.is_ok())

    async def test_project_owner_can_read_other_user_permissions_via_inherited_rw(
        self,
    ):
        """Project owner should read another user's permissions via inherited RW."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._get_project_or_err = AsyncMock(
            return_value=Ok((1, "org-1", active_info))
        )
        service._get_member_permissions = AsyncMock(
            return_value=Ok([ProjectPermission.OWNER.value])
        )

        # Act
        result = await service.authorize_project_permission(
            "project-uuid",
            "u-owner",
            ProjectPermission.USERS_PERMISSIONS_RW,
        )

        # Assert
        self.assertTrue(result.is_ok())

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

    async def test_create_project_success_sets_owner_permission_attribute(self):
        """Creating a project should add owner permission in flat attr form."""
        # Arrange
        service = self._make_service()
        service._has_org_wide_project_permission = AsyncMock(
            return_value=Ok(True)
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
        service.membership_repo.upsert_membership = AsyncMock(
            return_value=SimpleNamespace()
        )
        service._set_project_permissions = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.create_project("u1", "org-1", "p1", None)

        # Assert
        self.assertTrue(res.is_ok())
        service._set_project_permissions.assert_awaited_once_with(
            "u1", "proj-1", ["project.owner"]
        )
        self.session_manager.session.commit.assert_awaited()

    async def test_create_project_fails_when_owner_attr_write_fails(self):
        """Project creation should surface attr-write failure before commit."""
        # Arrange
        service = self._make_service()
        service._has_org_wide_project_permission = AsyncMock(
            return_value=Ok(True)
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
        service.membership_repo.upsert_membership = AsyncMock(
            return_value=SimpleNamespace()
        )
        service._set_project_permissions = AsyncMock(
            return_value=Err(_DummyError("kc write failed"))
        )

        # Act
        res = await service.create_project("u1", "org-1", "p1", None)

        # Assert
        self.assertTrue(res.is_err())
        self.session_manager.session.commit.assert_not_awaited()

    async def test_create_project_propagates_org_wide_permission_lookup_error(
        self,
    ):
        """Project creation should return upstream org-wide permission lookup errors."""
        # Arrange
        service = self._make_service()
        service._has_org_wide_project_permission = AsyncMock(
            return_value=Err(_DummyError("kc failed"))
        )

        # Act
        res = await service.create_project("u1", "org-1", "p1", None)

        # Assert
        self.assertTrue(res.is_err())

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

    async def test_list_user_projects_with_org_filter_checks_membership(self):
        """Org-scoped project listing should validate org membership first."""
        # Arrange
        service = self._make_service()
        service._ensure_user_in_org = AsyncMock(return_value=Ok(None))
        service.project_repo.list_by_member = AsyncMock(return_value=[])

        # Act
        res = await service.list_user_projects("u1", "org-1")

        # Assert
        self.assertTrue(res.is_ok())
        service._ensure_user_in_org.assert_awaited_once_with("u1", "org-1")

    async def test_has_org_wide_permission_true_and_false(self):
        """Org-wide permission check should respect membership permissions."""
        # Arrange
        service = self._make_service()
        service.project_repo.list_by_member = AsyncMock(
            return_value=[
                SimpleNamespace(uuid="proj-1"),
                SimpleNamespace(uuid="proj-2"),
            ]
        )
        service._get_permissions_from_attrs = AsyncMock(
            side_effect=[
                Ok(["project.settings.read"]),
                Ok(["projects.get_all"]),
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
        service.project_repo.list_by_member = AsyncMock(
            return_value=[SimpleNamespace(uuid="proj-1")]
        )
        service._get_permissions_from_attrs = AsyncMock(
            return_value=Ok(["project.settings.read"])
        )

        # Act
        false_res = await service._has_org_wide_project_permission(
            "u1", "org-1", ProjectPermission.PROJECTS_CREATE
        )

        # Assert
        self.assertTrue(false_res.is_ok())
        self.assertFalse(false_res.unwrap())

    async def test_has_org_wide_permission_uses_project_uuids_for_each_joined_project(
        self,
    ):
        """Org-wide checks should evaluate every joined project uuid."""
        # Arrange
        service = self._make_service()
        service.project_repo.list_by_member = AsyncMock(
            return_value=[
                SimpleNamespace(uuid="proj-a"),
                SimpleNamespace(uuid="proj-b"),
            ]
        )
        service._get_permissions_from_attrs = AsyncMock(
            side_effect=[Ok([]), Ok(["projects.create"])]
        )

        # Act
        res = await service._has_org_wide_project_permission(
            "actor",
            "org-1",
            ProjectPermission.PROJECTS_CREATE,
        )

        # Assert
        self.assertTrue(res.is_ok())
        self.assertTrue(res.unwrap())
        self.assertEqual(
            service._get_permissions_from_attrs.await_args_list,
            [
                unittest.mock.call("actor", "proj-a"),
                unittest.mock.call("actor", "proj-b"),
            ],
        )

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

    async def test_list_org_projects_denied_without_org_wide_permission(self):
        """Org project listing should fail without projects.get_all."""
        # Arrange
        service = self._make_service()
        service._has_org_wide_project_permission = AsyncMock(
            return_value=Ok(False)
        )

        # Act
        res = await service.list_org_projects("u1", "org-1")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, InsufficientProjectPermissionError)
