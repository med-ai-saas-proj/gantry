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
    OwnerRequiredForGrantError,
    InvalidProjectPermissionError,
    LastOwnerRemovalNotAllowedError,
    _DummyError,
    encode_project_permission,
)


class TestProjectServicePermissionUpdates(BaseProjectServiceTest):
    """Project service tests grouped by category."""

    async def test_update_user_permissions_invalid_permission(self):
        """Unknown permission values must be rejected."""
        # Arrange
        service = self._make_service()

        # Act
        res = await service.updateUserPermissions(
            "proj-1", "actor", "target", ["bogus.permission"]
        )

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), InvalidProjectPermissionError)

    async def test_update_user_permissions_owner_required_for_rw_grant(self):
        """Only project owner can grant users.permissions.read_write."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._getMemberPermissions = AsyncMock(
            return_value=Ok(["project.users.permissions.read_write"])
        )
        service.membership_repo.getMembership = AsyncMock(
            return_value=SimpleNamespace(user_id="target")
        )

        # Act
        res = await service.updateUserPermissions(
            "proj-1",
            "actor",
            "target",
            ["project.users.permissions.read_write"],
        )

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), OwnerRequiredForGrantError)

    async def test_update_user_permissions_target_not_in_project(self):
        """Updating permissions should fail if target is not a project member."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._getMemberPermissions = AsyncMock(
            return_value=Ok(["project.owner"])
        )
        service.membership_repo.getMembership = AsyncMock(return_value=None)

        # Act
        res = await service.updateUserPermissions(
            "proj-1", "actor", "target", ["project.settings.read"]
        )

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), UserNotInProjectError)

    async def test_update_user_permissions_success(self):
        """Valid permission update should persist and return updated set."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._getMemberPermissions = AsyncMock(
            return_value=Ok(["project.owner"])
        )
        service.membership_repo.getMembership = AsyncMock(
            return_value=SimpleNamespace(user_id="target")
        )
        service._getPermissionsFromAttrs = AsyncMock(
            return_value=Ok(["project.settings.read"])
        )
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
        res = await service.updateUserPermissions(
            "proj-1",
            "actor",
            "target",
            ["project.settings.write"],
        )

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().permissions, ["project.settings.write"])
        service.kc.getUserAttributes.assert_awaited_once_with("target")
        service.kc.setUserAttribute.assert_awaited_once_with(
            "target",
            PROJECT_PERMISSIONS_ATTR,
            [
                encode_project_permission(
                    "other-proj", "project.settings.read"
                ),
                encode_project_permission("proj-1", "project.settings.write"),
            ],
        )

    async def test_project_owner_can_update_other_user_permissions(self):
        """Project owner should update another member's permissions."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._getMemberPermissions = AsyncMock(
            return_value=Ok([ProjectPermission.OWNER.value])
        )
        service.membership_repo.getMembership = AsyncMock(
            return_value=SimpleNamespace(user_id="target")
        )
        service._getPermissionsFromAttrs = AsyncMock(return_value=Ok([]))
        service.kc.getUserAttributes = AsyncMock(return_value=Ok({}))
        service.kc.setUserAttribute = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.updateUserPermissions(
            "proj-1",
            "u-owner",
            "target",
            ["project.users.get_all"],
        )

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().permissions, ["project.users.get_all"])

    async def test_update_user_permissions_cannot_remove_last_owner(self):
        """Permission updates should reject stripping owner from the last owner."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._getMemberPermissions = AsyncMock(
            return_value=Ok(["project.owner"])
        )
        service.membership_repo.getMembership = AsyncMock(
            return_value=SimpleNamespace(user_id="target")
        )
        service._getPermissionsFromAttrs = AsyncMock(
            return_value=Ok(["project.owner"])
        )
        service._countProjectOwners = AsyncMock(return_value=Ok(1))

        # Act
        res = await service.updateUserPermissions(
            "proj-1",
            "actor",
            "target",
            ["project.settings.read"],
        )

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), LastOwnerRemovalNotAllowedError)

    async def test_update_user_permissions_remove_owner_succeeds_with_multiple_owners(
        self,
    ):
        """Removing owner permission should succeed when another owner remains."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
        )
        service._getMemberPermissions = AsyncMock(
            return_value=Ok(["project.owner"])
        )
        service.membership_repo.getMembership = AsyncMock(
            return_value=SimpleNamespace(user_id="target")
        )
        service._getPermissionsFromAttrs = AsyncMock(
            return_value=Ok(["project.owner"])
        )
        service._countProjectOwners = AsyncMock(return_value=Ok(2))
        service.kc.getUserAttributes = AsyncMock(return_value=Ok({}))
        service.kc.setUserAttribute = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.updateUserPermissions(
            "proj-1", "actor", "target", ["project.settings.read"]
        )

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)

    async def test_update_user_permissions_propagates_target_perm_and_owner_count_errors(
        self,
    ):
        """Permission updates should surface target permission lookup and owner count errors."""
        # Arrange
        service = self._make_service()
        active_info = SimpleNamespace(archived=False)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", active_info))
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

        # Act
        target_perm_err = await service.updateUserPermissions(
            "proj-1", "actor", "target", ["project.settings.read"]
        )

        # Assert
        self.assertTrue(target_perm_err.status == ResultStatus.Err)

        # Arrange
        service._getPermissionsFromAttrs = AsyncMock(
            return_value=Ok(["project.owner"])
        )
        service._countProjectOwners = AsyncMock(
            return_value=Err(_DummyError("count failed"))
        )

        # Act
        owner_count_err = await service.updateUserPermissions(
            "proj-1", "actor", "target", []
        )

        # Assert
        self.assertTrue(owner_count_err.status == ResultStatus.Err)

    async def test_update_user_permissions_archived_project_denied(self):
        """Archived project should reject permission updates."""
        # Arrange
        service = self._make_service()
        archived_info = SimpleNamespace(archived=True)
        service._getProjectOrErr = AsyncMock(
            return_value=Ok((10, "org-1", archived_info))
        )

        # Act
        res = await service.updateUserPermissions(
            "proj-1", "actor", "target", ["project.settings.read"]
        )

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), ProjectArchivedError)
