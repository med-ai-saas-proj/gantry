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
    UserNotInProjectError,
    BaseProjectServiceTest,
    UserAlreadyInProjectError,
    LastOwnerRemovalNotAllowedError,
    unittest,
    _DummyError,
    encode_project_permission,
)


class TestProjectServiceMembership(BaseProjectServiceTest):
    """Project service tests grouped by category."""

    async def test_add_user_duplicate(self):
        """Adding an existing member should return duplicate error."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._ensureUserInOrg = AsyncMock(return_value=Ok(None))
        service.membership_repo.getMembership = AsyncMock(
            return_value=SimpleNamespace(user_id="u2")
        )

        # Act
        res = await service.addUserToProject("proj-1", "u2")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), UserAlreadyInProjectError)

    async def test_add_user_success(self):
        """Adding new user should create membership and commit."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._ensureUserInOrg = AsyncMock(return_value=Ok(None))
        service.membership_repo.getMembership = AsyncMock(return_value=None)
        service.membership_repo.upsertMembership = AsyncMock(
            return_value=SimpleNamespace()
        )
        service.kc.getUserAttributes = AsyncMock(return_value=Ok({}))
        service.kc.setUserAttribute = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.addUserToProject("proj-1", "u2")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.membership_repo = service.membership_repo
        self.membership_repo.upsertMembership.assert_awaited_once()
        service.kc.getUserAttributes.assert_awaited_once_with("u2")
        service.kc.setUserAttribute.assert_awaited_once_with(
            "u2",
            PROJECT_PERMISSIONS_ATTR,
            [],
        )
        self.session_manager.session.commit.assert_awaited()

    async def test_add_user_archived_project_denied(self):
        """Archived project should block adding new users."""
        # Arrange
        service = self._make_service()
        archived_info = SimpleNamespace(archived=True)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", archived_info))
        )

        # Act
        res = await service.addUserToProject("proj-1", "u2")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), ProjectArchivedError)

    async def test_add_user_target_must_belong_to_org(self):
        """Adding user should fail if target user is outside the organization."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._ensureUserInOrg = AsyncMock(
            return_value=Err(_DummyError("not in org"))
        )

        # Act
        res = await service.addUserToProject("proj-1", "u2")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)

    async def test_remove_last_owner_blocked(self):
        """Service must block removing the last project owner."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service.membership_repo.getMembership = AsyncMock(
            return_value=SimpleNamespace(user_id="u-owner")
        )
        service.membership_repo.listMembers = AsyncMock(
            return_value=[SimpleNamespace(user_id="u-owner")]
        )
        service._getPermissionsFromAttrs = AsyncMock(
            side_effect=[
                Ok(["project.owner"]),
                Ok(["project.owner"]),
            ]
        )

        # Act
        res = await service.removeUserFromProject("proj-1", "u-owner")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), LastOwnerRemovalNotAllowedError)

    async def test_count_project_owners_counts_owner_permissions_only(self):
        """Owner counting should use project-scoped attrs for each member id."""
        # Arrange
        service = self._make_service()
        service.membership_repo.listMembers = AsyncMock(
            return_value=[
                SimpleNamespace(user_id="u-owner"),
                SimpleNamespace(user_id="u-editor"),
                SimpleNamespace(user_id="u-owner-2"),
            ]
        )
        service._getPermissionsFromAttrs = AsyncMock(
            side_effect=[
                Ok(["project.owner"]),
                Ok(["project.settings.read"]),
                Ok(["project.owner", "projects.get_all"]),
            ]
        )

        # Act
        res = await service._countProjectOwners(10, "proj-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap(), 2)
        self.assertEqual(
            service._getPermissionsFromAttrs.await_args_list,
            [
                unittest.mock.call("u-owner", "proj-1"),
                unittest.mock.call("u-editor", "proj-1"),
                unittest.mock.call("u-owner-2", "proj-1"),
            ],
        )

    async def test_remove_user_success(self):
        """Removing a non-owner member should succeed and commit."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service.membership_repo.getMembership = AsyncMock(
            return_value=SimpleNamespace(user_id="u2")
        )
        service.membership_repo.deleteMembership = AsyncMock(return_value=True)
        service._getPermissionsFromAttrs = AsyncMock(return_value=Ok([]))
        service.kc.getUserAttributes = AsyncMock(
            return_value=Ok(
                {
                    PROJECT_PERMISSIONS_ATTR: [
                        encode_project_permission(
                            "other-proj", "project.settings.read"
                        )
                    ]
                }
            )
        )
        service.kc.setUserAttribute = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.removeUserFromProject("proj-1", "u2")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        service.membership_repo.deleteMembership.assert_awaited_once()
        service.kc.getUserAttributes.assert_awaited_once_with("u2")
        service.kc.setUserAttribute.assert_awaited_once_with(
            "u2",
            PROJECT_PERMISSIONS_ATTR,
            [encode_project_permission("other-proj", "project.settings.read")],
        )
        self.session_manager.session.commit.assert_awaited()

    async def test_remove_owner_succeeds_when_project_has_multiple_owners(self):
        """Removing one owner should succeed when another owner still exists."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service.membership_repo.getMembership = AsyncMock(
            return_value=SimpleNamespace(user_id="u-owner")
        )
        service._getPermissionsFromAttrs = AsyncMock(
            return_value=Ok(["project.owner"])
        )
        service._countProjectOwners = AsyncMock(return_value=Ok(2))
        service.membership_repo.deleteMembership = AsyncMock(return_value=True)
        service.kc.getUserAttributes = AsyncMock(return_value=Ok({}))
        service.kc.setUserAttribute = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.removeUserFromProject("proj-1", "u-owner")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)

    async def test_remove_user_propagates_permission_and_owner_count_errors(
        self,
    ):
        """User removal should surface permission lookup and owner count failures."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service.membership_repo.getMembership = AsyncMock(
            return_value=SimpleNamespace(user_id="u-owner")
        )
        service._getPermissionsFromAttrs = AsyncMock(
            return_value=Err(_DummyError("perm lookup failed"))
        )

        # Act
        perm_err = await service.removeUserFromProject("proj-1", "u-owner")

        # Assert
        self.assertTrue(perm_err.status == ResultStatus.Err)

        # Arrange
        service._getPermissionsFromAttrs = AsyncMock(
            return_value=Ok(["project.owner"])
        )
        service._countProjectOwners = AsyncMock(
            return_value=Err(_DummyError("count failed"))
        )

        # Act
        count_err = await service.removeUserFromProject("proj-1", "u-owner")

        # Assert
        self.assertTrue(count_err.status == ResultStatus.Err)

    async def test_remove_user_archived_project_denied(self):
        """Archived project should block membership removal."""
        # Arrange
        service = self._make_service()
        archived_info = SimpleNamespace(archived=True)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", archived_info))
        )

        # Act
        res = await service.removeUserFromProject("proj-1", "u2")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), ProjectArchivedError)

    async def test_remove_user_missing_membership_returns_not_found(self):
        """Removing absent membership should return user_not_in_project."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service.membership_repo.getMembership = AsyncMock(return_value=None)

        # Act
        res = await service.removeUserFromProject("proj-1", "u2")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), UserNotInProjectError)

    async def test_get_user_permissions_success(self):
        """Get user permissions should return current permission list."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._getMemberPermissions = AsyncMock(
            return_value=Ok(["project.settings.read"])
        )

        # Act
        res = await service.getUserPermissions("proj-1", "u2")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().permissions, ["project.settings.read"])

    async def test_get_user_permissions_project_isolation(self):
        """Reading permissions should ignore entries from other projects."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service.membership_repo.getMembership = AsyncMock(
            return_value=SimpleNamespace(user_id="u2")
        )
        service.kc.getUserAttributes = AsyncMock(
            return_value=Ok(
                {
                    PROJECT_PERMISSIONS_ATTR: [
                        encode_project_permission(
                            "proj-1", "project.settings.read"
                        ),
                        encode_project_permission("proj-2", "project.owner"),
                    ]
                }
            )
        )

        # Act
        res = await service.getUserPermissions("proj-1", "u2")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().permissions, ["project.settings.read"])

    async def test_get_user_permissions_archived_project_denied(self):
        """Archived project should reject permission reads."""
        # Arrange
        service = self._make_service()
        archived_info = SimpleNamespace(archived=True)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", archived_info))
        )

        # Act
        res = await service.getUserPermissions("proj-1", "u2")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), ProjectArchivedError)

    async def test_get_user_permissions_propagates_member_permission_error(
        self,
    ):
        """Permission reads should surface member-permission lookup failures."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._getMemberPermissions = AsyncMock(
            return_value=Err(_DummyError("perm lookup failed"))
        )

        # Act
        res = await service.getUserPermissions("proj-1", "u2")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
