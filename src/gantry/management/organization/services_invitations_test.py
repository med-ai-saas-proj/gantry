"""Category tests for organization service unit rules."""

from .services_test_support import (
    Ok,
    Err,
    AsyncMock,
    ResultStatus,
    OrgPermission,
    SimpleNamespace,
    OrgNotFoundError,
    BaseOrgServiceTest,
    OwnerTransferNotAllowedError,
    OwnerPermissionImmutableError,
    UserAlreadyInOrganizationError,
    UserAlreadyInAnotherOrganizationError,
    _DummyError,
)


class TestOrgServiceInvitations(BaseOrgServiceTest):
    """Organization service tests grouped by category."""

    async def test_create_invitation_conflict_when_user_already_in_org(self):
        """Inviting an existing member should return conflict."""
        # Arrange
        service = self._make_service()
        service.kc.findUserByEmail = AsyncMock(return_value=Ok({"id": "u1"}))
        service.kc.getMemberOrganizations = AsyncMock(
            return_value=Ok([{"id": "org-1"}])
        )

        # Act
        res = await service.createInvitation("org-1", "x@example.com")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), UserAlreadyInOrganizationError)

    async def test_create_invitation_conflict_when_user_in_other_org(self):
        """Inviting user from another org should return conflict."""
        # Arrange
        service = self._make_service()
        service.kc.findUserByEmail = AsyncMock(return_value=Ok({"id": "u1"}))
        service.kc.getMemberOrganizations = AsyncMock(
            return_value=Ok([{"id": "org-2"}])
        )

        # Act
        res = await service.createInvitation("org-1", "x@example.com")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), UserAlreadyInAnotherOrganizationError)

    async def test_create_invitation_success_for_new_email(self):
        """Inviting new email should call Keycloak invite endpoint."""
        # Arrange
        service = self._make_service()
        service.kc.findUserByEmail = AsyncMock(return_value=Ok(None))
        service.kc.inviteUser = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.createInvitation("org-1", "new@example.com")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        service.kc.inviteUser.assert_awaited_once()

    async def test_create_invitation_existing_user_without_orgs_is_allowed(
        self,
    ):
        """Existing Keycloak user with no org membership should still be inviteable."""
        # Arrange
        service = self._make_service()
        service.kc.findUserByEmail = AsyncMock(return_value=Ok({"id": "u1"}))
        service.kc.getMemberOrganizations = AsyncMock(return_value=Ok([]))
        service.kc.inviteUser = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.createInvitation("org-1", "existing@example.com")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        service.kc.inviteUser.assert_awaited_once()

    async def test_get_invitations_maps_keycloak_payload(self):
        """Invitation listing should map Keycloak invitation payloads to DTOs."""
        # Arrange
        service = self._make_service()
        service.kc.getInvitations = AsyncMock(
            return_value=Ok(
                [
                    {
                        "id": "inv-1",
                        "email": "a@test",
                        "status": "pending",
                    }
                ]
            )
        )

        # Act
        res = await service.getInvitations("org-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().results[0].id, "inv-1")

    async def test_get_invitation_maps_single_invitation(self):
        """Single invitation lookup should map Keycloak payload to DTO."""
        # Arrange
        service = self._make_service()
        service.kc.getInvitation = AsyncMock(
            return_value=Ok(
                {
                    "id": "inv-1",
                    "email": "a@test",
                    "status": "pending",
                }
            )
        )

        # Act
        res = await service.getInvitation("org-1", "inv-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().email, "a@test")

    async def test_delete_and_resend_invitation_delegate_to_keycloak(self):
        """Delete/resend invitation flows should delegate and return success."""
        # Arrange
        service = self._make_service()
        service.kc.deleteInvitation = AsyncMock(return_value=Ok(True))
        service.kc.resendInvitation = AsyncMock(return_value=Ok(True))

        # Act
        delete_res = await service.deleteInvitation("org-1", "inv-1")
        resend_res = await service.resendInvitation("org-1", "inv-1")

        # Assert
        self.assertTrue(delete_res.status == ResultStatus.Ok)
        self.assertTrue(resend_res.status == ResultStatus.Ok)

    async def test_get_org_owner_id_requires_exactly_one_owner(self):
        """Owner lookup should reject zero-owner and multi-owner states."""
        # Arrange
        service = self._make_service()
        service.kc.getOrgMembers = AsyncMock(return_value=Ok([]))

        # Act
        no_owner_res = await service._getOrgOwnerId("org-1")

        # Assert
        self.assertTrue(no_owner_res.status == ResultStatus.Err)
        from gantry.management.organization.services import OwnerNotFoundError

        self.assertIsInstance(no_owner_res.err(), OwnerNotFoundError)

        # Arrange
        service.kc.getOrgMembers = AsyncMock(
            side_effect=[
                Ok([{"id": "u1"}, {"id": "u2"}]),
                Ok([]),
            ]
        )
        service.kc.getUserAttributes = AsyncMock(
            side_effect=[
                Ok({"org_permissions": [OrgPermission.OWNER.value]}),
                Ok({"org_permissions": [OrgPermission.OWNER.value]}),
            ]
        )

        # Act
        multi_owner_res = await service._getOrgOwnerId("org-1")

        # Assert
        self.assertTrue(multi_owner_res.status == ResultStatus.Err)
        from gantry.management.organization.services import MultipleOwnersError

        self.assertIsInstance(multi_owner_res.err(), MultipleOwnersError)

    async def test_get_org_owner_id_single_owner_success(self):
        """Owner lookup should return the single owner id."""
        # Arrange
        service = self._make_service()
        service.kc.getOrgMembers = AsyncMock(
            side_effect=[Ok([{"id": "u1"}]), Ok([])]
        )
        service.kc.getUserAttributes = AsyncMock(
            return_value=Ok({"org_permissions": [OrgPermission.OWNER.value]})
        )

        # Act
        res = await service._getOrgOwnerId("org-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap(), "u1")

    async def test_get_org_owner_id_supports_paging_and_non_owner_members(self):
        """Owner lookup should advance pages and ignore non-owner members."""
        # Arrange
        service = self._make_service()
        first_page = [{"id": f"u{i}"} for i in range(100)]
        second_page = [{"id": "owner"}]
        service.kc.getOrgMembers = AsyncMock(
            side_effect=[Ok(first_page), Ok(second_page), Ok([])]
        )
        service.kc.getUserAttributes = AsyncMock(
            side_effect=[
                *(
                    Ok({"org_permissions": [OrgPermission.SETTINGS_READ.value]})
                    for _ in range(100)
                ),
                Ok({"org_permissions": [OrgPermission.OWNER.value]}),
            ]
        )

        # Act
        res = await service._getOrgOwnerId("org-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap(), "owner")
