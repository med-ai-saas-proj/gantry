"""Category tests for organization service unit rules."""

from .services_test_support import (
    Ok,
    Err,
    Mock,
    AsyncMock,
    OrgPermission,
    SimpleNamespace,
    OrgNotFoundError,
    BaseOrgServiceTest,
    InvalidPermissionError,
    OwnerRequiredForGrantError,
    OwnerTransferNotAllowedError,
    OwnerPermissionImmutableError,
    UserAlreadyInOrganizationError,
    MultipleOrganizationMembershipError,
    UserAlreadyInAnotherOrganizationError,
    ReadOwnPermissionsOrManageRequiredError,
    unittest,
    _DummyError,
    _extract_org_ids,
)


class TestOrgServicePermissions(BaseOrgServiceTest):
    """Organization service tests grouped by category."""

    def test_extract_org_ids_filters_missing(self):
        """Helper should return only non-empty org ids."""
        # Arrange
        orgs = [{"id": "a"}, {"name": "x"}, {"id": ""}, {"id": "b"}]

        # Act
        result = _extract_org_ids(orgs)

        # Assert
        self.assertEqual(result, {"a", "b"})

    async def test_ensure_org_exists_success(self):
        """Org existence helper should return Keycloak org payload."""
        # Arrange
        service = self._make_service()
        service.kc.get_org = AsyncMock(return_value=Ok({"id": "org-1"}))

        # Act
        res = await service._ensure_org_exists("org-1")

        # Assert
        self.assertTrue(res.is_ok())

    def test_extract_user_permissions_supports_string_and_list(self):
        """Extractor should normalize string/list and ignore invalid types."""
        # Arrange
        service = self._make_service()

        # Act
        from_string = service._extract_user_permissions(
            {"org_permissions": "organization.owner"}
        )
        from_list = service._extract_user_permissions(
            {"org_permissions": ["organization.invite", 123]}
        )
        from_invalid = service._extract_user_permissions(
            {"org_permissions": {"x": "y"}}
        )

        # Assert
        self.assertEqual(from_string, ["organization.owner"])
        self.assertEqual(from_list, ["organization.invite"])
        self.assertEqual(from_invalid, [])

    def test_flatten_settings_nested(self):
        """Nested settings should be flattened into dot-notation keys."""
        # Arrange
        service = self._make_service()
        data = {"a": {"b": {"c": 1}}, "x": 2}

        # Act
        flattened = service._flatten_settings(data)

        # Assert
        self.assertEqual(flattened, {"a.b.c": 1, "x": 2})

    async def test_ensure_user_in_org_multiple_memberships_denied(self):
        """User in multiple orgs should fail single-org invariant."""
        # Arrange
        service = self._make_service()
        service.kc.get_member_organizations = AsyncMock(
            return_value=Ok([{"id": "org-1"}, {"id": "org-2"}])
        )

        # Act
        res = await service._ensure_user_in_org("org-1", "u1")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, MultipleOrganizationMembershipError)

    async def test_ensure_user_in_org_success_and_missing_org(self):
        """Membership helper should return Ok for same org and Err for different org."""
        # Arrange
        service = self._make_service()
        service.kc.get_member_organizations = AsyncMock(
            return_value=Ok([{"id": "org-1"}])
        )

        # Act
        ok_res = await service._ensure_user_in_org("org-1", "u1")

        # Assert
        self.assertTrue(ok_res.is_ok())

        # Arrange
        service.kc.get_member_organizations = AsyncMock(
            return_value=Ok([{"id": "org-2"}])
        )

        # Act
        missing_res = await service._ensure_user_in_org("org-1", "u1")

        # Assert
        self.assertTrue(missing_res.is_err())

    async def test_ensure_can_read_user_permissions_self_allowed(self):
        """User should always be able to read their own org permissions."""
        # Arrange
        service = self._make_service()
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.ensure_can_read_user_permissions(
            org_id="org-1",
            actor_user_id="u1",
            target_user_id="u1",
        )

        # Assert
        self.assertTrue(res.is_ok())

    async def test_ensure_can_read_user_permissions_other_user_requires_rw(
        self,
    ):
        """Reading another user's permissions requires manage permission."""
        # Arrange
        service = self._make_service()
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))
        service._get_member_permissions = AsyncMock(
            return_value=Ok([OrgPermission.SETTINGS_READ.value])
        )

        # Act
        res = await service.ensure_can_read_user_permissions(
            org_id="org-1",
            actor_user_id="u1",
            target_user_id="u2",
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(
            res.error, ReadOwnPermissionsOrManageRequiredError
        )

    async def test_ensure_can_read_user_permissions_service_actor_bypass(self):
        """Trusted backend service-account should bypass read checks."""
        # Arrange
        service = self._make_service()

        # Act
        res = await service.ensure_can_read_user_permissions(
            org_id="org-1",
            actor_user_id="svc",
            target_user_id="u2",
            actor_is_service_account=True,
            actor_client_id="med-ai-saas-backend",
        )

        # Assert
        self.assertTrue(res.is_ok())

    async def test_ensure_can_read_user_permissions_other_user_allowed_with_rw(
        self,
    ):
        """Reading another user's permissions should pass with manage permission."""
        # Arrange
        service = self._make_service()
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))
        service._get_member_permissions = AsyncMock(
            return_value=Ok([OrgPermission.USERS_PERMISSIONS_RW.value])
        )

        # Act
        res = await service.ensure_can_read_user_permissions(
            org_id="org-1",
            actor_user_id="u1",
            target_user_id="u2",
        )

        # Assert
        self.assertTrue(res.is_ok())

    async def test_owner_can_read_other_user_permissions_via_inherited_rw(self):
        """Organization owner should read another user's permissions via inheritance."""
        # Arrange
        service = self._make_service()
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))
        service._get_member_permissions = AsyncMock(
            return_value=Ok([OrgPermission.OWNER.value])
        )

        # Act
        res = await service.ensure_can_read_user_permissions(
            org_id="org-1",
            actor_user_id="u-owner",
            target_user_id="u-member",
        )

        # Assert
        self.assertTrue(res.is_ok())

    async def test_update_user_permissions_rejects_invalid(self):
        """Service must reject unknown org permission values."""
        # Arrange
        service = self._make_service()

        # Act
        res = await service.update_user_permissions(
            org_id="org-1",
            actor_user_id="u1",
            user_id="u2",
            permissions=["organization.owner", "bogus.permission"],
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, InvalidPermissionError)

    async def test_update_user_permissions_owner_permission_immutable(self):
        """Owner cannot lose organization.owner permission."""
        # Arrange
        service = self._make_service()
        service._get_org_owner_id = AsyncMock(return_value=Ok("u1"))
        service._get_member_permissions = AsyncMock(
            return_value=Ok([OrgPermission.OWNER.value])
        )
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.update_user_permissions(
            org_id="org-1",
            actor_user_id="u1",
            user_id="u1",
            permissions=[OrgPermission.SETTINGS_READ.value],
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, OwnerPermissionImmutableError)

    async def test_update_user_permissions_owner_transfer_not_allowed(self):
        """Cannot assign organization.owner to a non-owner user."""
        # Arrange
        service = self._make_service()
        service._get_org_owner_id = AsyncMock(return_value=Ok("u-owner"))
        service._get_member_permissions = AsyncMock(
            return_value=Ok([OrgPermission.OWNER.value])
        )
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.update_user_permissions(
            org_id="org-1",
            actor_user_id="u-owner",
            user_id="u-other",
            permissions=[OrgPermission.OWNER.value],
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, OwnerTransferNotAllowedError)

    async def test_update_user_permissions_grant_rw_requires_owner(self):
        """Only org owner can grant users.permissions.read_write."""
        # Arrange
        service = self._make_service()
        service._get_org_owner_id = AsyncMock(return_value=Ok("owner"))
        service._get_member_permissions = AsyncMock(
            return_value=Ok([OrgPermission.SETTINGS_READ.value])
        )
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.update_user_permissions(
            org_id="org-1",
            actor_user_id="u-actor",
            user_id="u-target",
            permissions=[OrgPermission.USERS_PERMISSIONS_RW.value],
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, OwnerRequiredForGrantError)

    async def test_update_user_permissions_success(self):
        """Valid permission update should persist via Keycloak attribute."""
        # Arrange
        service = self._make_service()
        service._get_org_owner_id = AsyncMock(return_value=Ok("u-owner"))
        service._get_member_permissions = AsyncMock(
            return_value=Ok([OrgPermission.OWNER.value])
        )
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))
        service.kc.set_user_attribute = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.update_user_permissions(
            org_id="org-1",
            actor_user_id="u-owner",
            user_id="u-target",
            permissions=[OrgPermission.SETTINGS_READ.value],
        )

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(
            res.unwrap().permissions, [OrgPermission.SETTINGS_READ.value]
        )
        service.kc.set_user_attribute.assert_awaited_once()

    async def test_owner_can_update_other_user_permissions_in_org(self):
        """Organization owner should update another member's permissions."""
        # Arrange
        service = self._make_service()
        service._get_org_owner_id = AsyncMock(return_value=Ok("u-owner"))
        service._get_member_permissions = AsyncMock(
            return_value=Ok([OrgPermission.OWNER.value])
        )
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))
        service.kc.set_user_attribute = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.update_user_permissions(
            org_id="org-1",
            actor_user_id="u-owner",
            user_id="u-member",
            permissions=[OrgPermission.USERS_GET_ALL.value],
        )

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(
            res.unwrap().permissions,
            [OrgPermission.USERS_GET_ALL.value],
        )

    async def test_update_user_permissions_service_actor_bypass_owner_checks(
        self,
    ):
        """Trusted backend service-account should update org permissions directly."""
        # Arrange
        service = self._make_service()
        service.kc.set_user_attribute = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.update_user_permissions(
            org_id="org-1",
            actor_user_id="svc",
            user_id="u-target",
            permissions=[OrgPermission.SETTINGS_READ.value],
            actor_is_service_account=True,
            actor_client_id="med-ai-saas-backend",
        )

        # Assert
        self.assertTrue(res.is_ok())
        service.kc.set_user_attribute.assert_awaited_once_with(
            "u-target",
            "org_permissions",
            [OrgPermission.SETTINGS_READ.value],
        )

    async def test_get_user_permissions_success(self):
        """Reading org permissions should return the current member permission list."""
        # Arrange
        service = self._make_service()
        service._get_member_permissions = AsyncMock(
            return_value=Ok([OrgPermission.SETTINGS_READ.value])
        )

        # Act
        res = await service.get_user_permissions("org-1", "u-member")

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(
            res.unwrap().permissions,
            [OrgPermission.SETTINGS_READ.value],
        )

    async def test_get_member_permissions_success(self):
        """Direct member permission lookup should read org_permissions from attrs."""
        # Arrange
        service = self._make_service()
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))
        service.kc.get_user_attributes = AsyncMock(
            return_value=Ok({"org_permissions": [OrgPermission.OWNER.value]})
        )

        # Act
        res = await service._get_member_permissions("org-1", "u1")

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap(), [OrgPermission.OWNER.value])

    async def test_get_member_permissions_propagates_membership_error(self):
        """Direct member permission lookup should stop when org membership check fails."""
        # Arrange
        service = self._make_service()
        service._ensure_user_in_org = AsyncMock(
            return_value=Err(_DummyError("not in org"))
        )

        # Act
        res = await service._get_member_permissions("org-1", "u1")

        # Assert
        self.assertTrue(res.is_err())

    async def test_get_user_permissions_target_not_in_org(self):
        """Reading org permissions should fail if target is outside org."""
        # Arrange
        service = self._make_service()
        service._get_member_permissions = AsyncMock(
            return_value=Err(OrgNotFoundError())
        )

        # Act
        res = await service.get_user_permissions("org-1", "u-missing")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, OrgNotFoundError)
