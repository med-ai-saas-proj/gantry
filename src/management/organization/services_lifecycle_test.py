"""Category tests for organization service unit rules."""

from .services_test_support import (
    UTC,
    Ok,
    Err,
    AsyncMock,
    OrgPermission,
    SimpleNamespace,
    OrgNotFoundError,
    BaseOrgServiceTest,
    OwnerRemovalNotAllowedError,
    DeletionRequestNotFoundError,
    OwnerPermissionRequiredError,
    DeletionAlreadyRequestedError,
    datetime,
    _DummyError,
)


class TestOrgServiceLifecycle(BaseOrgServiceTest):
    """Organization service tests grouped by category."""

    async def test_remove_owner_not_allowed(self):
        """Organization owner removal should be blocked."""
        # Arrange
        service = self._make_service()
        service._get_org_owner_id = AsyncMock(return_value=Ok("owner"))

        # Act
        res = await service.remove_user("org-1", "owner")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, OwnerRemovalNotAllowedError)

    async def test_request_delete_org_conflict_when_already_requested(self):
        """Requesting deletion twice should return conflict."""
        # Arrange
        service = self._make_service()
        service._ensure_org_exists = AsyncMock(return_value=Ok({"id": "org-1"}))
        service.deletion_repo.get_by_org_id = AsyncMock(
            return_value=SimpleNamespace(id=1)
        )

        # Act
        res = await service.request_delete_org("org-1")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, DeletionAlreadyRequestedError)

    async def test_request_delete_org_success(self):
        """Deletion request should return timestamps and commit."""
        # Arrange
        service = self._make_service()
        now = datetime(2026, 3, 13, 10, 0, tzinfo=UTC).replace(tzinfo=None)
        service._ensure_org_exists = AsyncMock(return_value=Ok({"id": "org-1"}))
        service.deletion_repo.get_by_org_id = AsyncMock(return_value=None)
        service.deletion_repo.upsert_request = AsyncMock(
            return_value=SimpleNamespace(requested_at=now)
        )

        # Act
        res = await service.request_delete_org("org-1")

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().org_id, "org-1")
        self.session_manager.session.commit.assert_awaited()

    async def test_cancel_delete_org_not_found(self):
        """Cancel should fail if there is no pending deletion request."""
        # Arrange
        service = self._make_service()
        service.deletion_repo.delete_by_org_id = AsyncMock(return_value=False)

        # Act
        res = await service.cancel_delete_org("org-1")

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, DeletionRequestNotFoundError)

    async def test_cancel_delete_org_success(self):
        """Cancel should delete pending request and commit."""
        # Arrange
        service = self._make_service()
        service.deletion_repo.delete_by_org_id = AsyncMock(return_value=True)

        # Act
        res = await service.cancel_delete_org("org-1")

        # Assert
        self.assertTrue(res.is_ok())
        self.assertTrue(res.unwrap())
        self.session_manager.session.commit.assert_awaited()

    async def test_update_org_info_requires_owner(self):
        """Non-owner actor cannot update org metadata."""
        # Arrange
        service = self._make_service()
        service._get_org_owner_id = AsyncMock(return_value=Ok("u-owner"))

        # Act
        res = await service.update_org_info(
            org_id="org-1",
            actor_user_id="u-not-owner",
            name="new-name",
        )

        # Assert
        self.assertTrue(res.is_err())
        self.assertIsInstance(res.error, OwnerPermissionRequiredError)

    async def test_update_org_info_service_actor_bypass_owner_check(self):
        """Trusted backend service account should update org metadata directly."""
        # Arrange
        service = self._make_service()
        service.kc.get_org = AsyncMock(
            return_value=Ok({"id": "org-1", "name": "old-name"})
        )
        service.kc.update_org = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.update_org_info(
            org_id="org-1",
            actor_user_id="svc",
            name="new-name",
            actor_is_service_account=True,
            actor_client_id="med-ai-saas-backend",
        )

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().name, "new-name")
        self.assertIsNone(res.unwrap().owner_id)
        service.kc.update_org.assert_awaited_once_with(
            "org-1",
            {"id": "org-1", "name": "new-name"},
        )

    async def test_update_org_info_owner_success(self):
        """Organization owner should be able to rename the organization."""
        # Arrange
        service = self._make_service()
        service._get_org_owner_id = AsyncMock(return_value=Ok("u-owner"))
        service.kc.get_org = AsyncMock(
            return_value=Ok({"id": "org-1", "name": "old-name"})
        )
        service.kc.update_org = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.update_org_info(
            org_id="org-1",
            actor_user_id="u-owner",
            name="new-name",
        )

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().owner_id, "u-owner")

    async def test_get_org_info_without_owner_returns_owner_id_none(self):
        """Org info should still resolve when no owner attribute exists yet."""
        # Arrange
        service = self._make_service()
        service.kc.get_org = AsyncMock(
            return_value=Ok({"id": "org-1", "name": "Org One"})
        )
        from src.management.organization.services import OwnerNotFoundError

        service._get_org_owner_id = AsyncMock(
            return_value=Err(OwnerNotFoundError())
        )

        # Act
        res = await service.get_org_info("org-1")

        # Assert
        self.assertTrue(res.is_ok())
        self.assertIsNone(res.unwrap().owner_id)

    async def test_get_org_info_with_owner_success(self):
        """Org info should include resolved owner id when exactly one owner exists."""
        # Arrange
        service = self._make_service()
        service.kc.get_org = AsyncMock(
            return_value=Ok({"id": "org-1", "name": "Org One"})
        )
        service._get_org_owner_id = AsyncMock(return_value=Ok("u1"))

        # Act
        res = await service.get_org_info("org-1")

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().owner_id, "u1")

    async def test_get_settings_success(self):
        """Get settings should return repository values and commit session."""
        # Arrange
        service = self._make_service()
        service._ensure_org_exists = AsyncMock(return_value=Ok({"id": "org-1"}))
        service.settings_repo.get_or_create = AsyncMock(
            return_value=SimpleNamespace(rate_limit=100, extra={"a": 1})
        )

        # Act
        res = await service.get_settings("org-1")

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().rate_limit, 100)
        self.assertEqual(res.unwrap().extra, {"a": 1})

    async def test_process_due_deletions_deletes_org_and_cleans_records(self):
        """Deletion worker should delete due orgs and clean DB records."""
        # Arrange
        service = self._make_service()
        due_request = SimpleNamespace(org_id="org-1")
        service.deletion_repo.list_due_requests = AsyncMock(
            return_value=[due_request]
        )
        service.kc.delete_org = AsyncMock(return_value=Ok(True))
        service.settings_repo.delete_by_org_id = AsyncMock(return_value=True)
        service.deletion_repo.delete_by_org_id = AsyncMock(return_value=True)

        # Act
        processed = await service.process_due_deletions(batch_size=10)

        # Assert
        self.assertEqual(processed, 1)
        service.kc.delete_org.assert_awaited_once_with("org-1")
        service.settings_repo.delete_by_org_id.assert_awaited_once()
        self.session_manager.session.commit.assert_awaited()

    async def test_process_due_deletions_skips_failed_keycloak_delete(self):
        """Deletion worker should continue when Keycloak deletion fails."""
        # Arrange
        service = self._make_service()
        due_request = SimpleNamespace(org_id="org-1")
        service.deletion_repo.list_due_requests = AsyncMock(
            return_value=[due_request]
        )
        service.kc.delete_org = AsyncMock(
            return_value=Err(DeletionAlreadyRequestedError())
        )
        service.settings_repo.delete_by_org_id = AsyncMock()
        service.deletion_repo.delete_by_org_id = AsyncMock()

        # Act
        processed = await service.process_due_deletions(batch_size=10)

        # Assert
        self.assertEqual(processed, 0)
        service.settings_repo.delete_by_org_id.assert_not_called()
        service.deletion_repo.delete_by_org_id.assert_not_called()

    async def test_process_due_deletions_treats_missing_org_as_processed(self):
        """Deletion worker should still cleanup local records if org is already gone."""
        # Arrange
        service = self._make_service()
        due_request = SimpleNamespace(org_id="org-1")
        service.deletion_repo.list_due_requests = AsyncMock(
            return_value=[due_request]
        )
        service.kc.delete_org = AsyncMock(return_value=Err(OrgNotFoundError()))
        service.settings_repo.delete_by_org_id = AsyncMock(return_value=True)
        service.deletion_repo.delete_by_org_id = AsyncMock(return_value=True)

        # Act
        processed = await service.process_due_deletions(batch_size=10)

        # Assert
        self.assertEqual(processed, 1)
        service.settings_repo.delete_by_org_id.assert_awaited_once_with(
            self.session_manager.session, "org-1"
        )

    async def test_get_users_falls_back_to_member_count_when_count_fails(self):
        """User listing should fall back to page length if count lookup fails."""
        # Arrange
        service = self._make_service()
        service.kc.get_org_members = AsyncMock(
            return_value=Ok(
                [
                    {"id": "u1", "username": "one", "email": "1@test"},
                    {"id": "u2", "username": "two", "email": "2@test"},
                ]
            )
        )
        service.kc.get_org_member_count = AsyncMock(
            return_value=Err(OrgNotFoundError())
        )

        # Act
        res = await service.get_users("org-1", limit=20, offset=0)

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().total, 2)

    async def test_remove_user_success_deletes_member_record_and_user(self):
        """Removing non-owner user should remove org membership then delete user."""
        # Arrange
        service = self._make_service()
        service._get_org_owner_id = AsyncMock(return_value=Ok("owner"))
        service.kc.remove_member = AsyncMock(return_value=Ok(True))
        service.kc.delete_user = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.remove_user("org-1", "u-member")

        # Assert
        self.assertTrue(res.is_ok())
        service.kc.remove_member.assert_awaited_once_with("org-1", "u-member")
        service.kc.delete_user.assert_awaited_once_with("u-member")

    async def test_update_settings_flattens_nested_extra(self):
        """Update settings should flatten nested extra keys before upsert."""
        # Arrange
        service = self._make_service()
        service._ensure_org_exists = AsyncMock(return_value=Ok({"id": "org-1"}))
        service.settings_repo.upsert = AsyncMock(
            return_value=SimpleNamespace(
                rate_limit=90,
                extra={"a.b": 1, "x": 2},
            )
        )

        # Act
        res = await service.update_settings(
            org_id="org-1",
            rate_limit=90,
            extra={"a": {"b": 1}, "x": 2},
        )

        # Assert
        self.assertTrue(res.is_ok())
        self.assertEqual(res.unwrap().extra, {"a.b": 1, "x": 2})
        service.settings_repo.upsert.assert_awaited_once()

    async def test_misc_org_error_propagation_paths(self):
        """Org service should propagate upstream collaborator errors on edge paths."""
        # Arrange
        service = self._make_service()
        service.kc.get_org = AsyncMock(return_value=Ok({"id": "org-1"}))

        # _ensure_user_in_org -> kc lookup error
        service.kc.get_member_organizations = AsyncMock(
            return_value=Err(_DummyError("org lookup failed"))
        )
        ensure_err = await service._ensure_user_in_org("org-1", "u1")
        self.assertTrue(ensure_err.is_err())

        # _get_member_permissions -> attribute error
        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))
        service.kc.get_user_attributes = AsyncMock(
            return_value=Err(_DummyError("attr failed"))
        )
        member_perm_err = await service._get_member_permissions("org-1", "u1")
        self.assertTrue(member_perm_err.is_err())

        # _get_org_owner_id -> member page error, skip blank ids, attr error
        service.kc.get_org_members = AsyncMock(
            return_value=Err(_DummyError("member page failed"))
        )
        owner_page_err = await service._get_org_owner_id("org-1")
        self.assertTrue(owner_page_err.is_err())

        service.kc.get_org_members = AsyncMock(
            side_effect=[
                Ok([{"id": ""}, {"id": "u1"}]),
                Ok([]),
            ]
        )
        service.kc.get_user_attributes = AsyncMock(
            return_value=Err(_DummyError("owner attr failed"))
        )
        owner_attr_err = await service._get_org_owner_id("org-1")
        self.assertTrue(owner_attr_err.is_err())

        # _sync_metadata_from_keycloak -> org error and owner error
        service.kc.get_org = AsyncMock(
            return_value=Err(_DummyError("org failed"))
        )
        org_info_err = await service.get_org_info("org-1")
        self.assertTrue(org_info_err.is_err())

        service.kc.get_org = AsyncMock(return_value=Ok({"id": "org-1"}))
        service._get_org_owner_id = AsyncMock(
            return_value=Err(_DummyError("owner failed"))
        )
        owner_info_err = await service.get_org_info("org-1")
        self.assertTrue(owner_info_err.is_err())

        # request_delete_org/get_settings/update_settings -> org not found
        service._ensure_org_exists = AsyncMock(
            return_value=Err(OrgNotFoundError())
        )
        delete_req_err = await service.request_delete_org("org-1")
        get_settings_err = await service.get_settings("org-1")
        update_settings_err = await service.update_settings("org-1", 10, {})
        self.assertTrue(delete_req_err.is_err())
        self.assertTrue(get_settings_err.is_err())
        self.assertTrue(update_settings_err.is_err())

        # update_org_info -> owner lookup error, get_org error, update_org error
        service._get_org_owner_id = AsyncMock(
            return_value=Err(_DummyError("owner lookup failed"))
        )
        update_owner_err = await service.update_org_info(
            "org-1", "u1", "new-name"
        )
        self.assertTrue(update_owner_err.is_err())

        service._get_org_owner_id = AsyncMock(return_value=Ok("u1"))
        service.kc.get_org = AsyncMock(
            return_value=Err(_DummyError("org failed"))
        )
        update_get_org_err = await service.update_org_info(
            "org-1", "u1", "new-name"
        )
        self.assertTrue(update_get_org_err.is_err())

        service.kc.get_org = AsyncMock(return_value=Ok({"id": "org-1"}))
        service.kc.update_org = AsyncMock(
            return_value=Err(_DummyError("update failed"))
        )
        update_write_err = await service.update_org_info(
            "org-1", "u1", "new-name"
        )
        self.assertTrue(update_write_err.is_err())

        # get_users/remove_user/invitation read+write paths
        service.kc.get_org_members = AsyncMock(
            return_value=Err(_DummyError("get members failed"))
        )
        users_err = await service.get_users("org-1")
        self.assertTrue(users_err.is_err())

        service._get_org_owner_id = AsyncMock(
            return_value=Err(_DummyError("owner remove failed"))
        )
        remove_owner_err = await service.remove_user("org-1", "u2")
        self.assertTrue(remove_owner_err.is_err())

        service._get_org_owner_id = AsyncMock(return_value=Ok("owner"))
        service.kc.remove_member = AsyncMock(
            return_value=Err(_DummyError("remove failed"))
        )
        remove_member_err = await service.remove_user("org-1", "u2")
        self.assertTrue(remove_member_err.is_err())

        service.kc.get_invitations = AsyncMock(
            return_value=Err(_DummyError("list invites failed"))
        )
        service.kc.get_invitation = AsyncMock(
            return_value=Err(_DummyError("get invite failed"))
        )
        self.assertTrue((await service.get_invitations("org-1")).is_err())
        self.assertTrue(
            (await service.get_invitation("org-1", "inv-1")).is_err()
        )

        service.kc.find_user_by_email = AsyncMock(
            return_value=Err(_DummyError("find failed"))
        )
        self.assertTrue(
            (await service.create_invitation("org-1", "a@test")).is_err()
        )

        service.kc.find_user_by_email = AsyncMock(return_value=Ok({"id": "u1"}))
        service.kc.get_member_organizations = AsyncMock(
            return_value=Err(_DummyError("member orgs failed"))
        )
        self.assertTrue(
            (await service.create_invitation("org-1", "a@test")).is_err()
        )

        service.kc.find_user_by_email = AsyncMock(return_value=Ok(None))
        service.kc.invite_user = AsyncMock(
            return_value=Err(_DummyError("invite failed"))
        )
        self.assertTrue(
            (await service.create_invitation("org-1", "a@test")).is_err()
        )

        # ensure_can_read/update_user_permissions -> target/actor/write errors
        service._ensure_user_in_org = AsyncMock(
            return_value=Err(_DummyError("target missing"))
        )
        read_target_err = await service.ensure_can_read_user_permissions(
            "org-1", "u1", "u2"
        )
        self.assertTrue(read_target_err.is_err())

        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))
        service._get_member_permissions = AsyncMock(
            return_value=Err(_DummyError("actor perms failed"))
        )
        read_actor_err = await service.ensure_can_read_user_permissions(
            "org-1", "u1", "u2"
        )
        self.assertTrue(read_actor_err.is_err())

        service._get_org_owner_id = AsyncMock(
            return_value=Err(_DummyError("owner failed"))
        )
        update_owner_lookup_err = await service.update_user_permissions(
            "org-1", "u1", "u2", [OrgPermission.SETTINGS_READ.value]
        )
        self.assertTrue(update_owner_lookup_err.is_err())

        service._get_org_owner_id = AsyncMock(return_value=Ok("owner"))
        service._get_member_permissions = AsyncMock(
            return_value=Err(_DummyError("actor perms failed"))
        )
        update_actor_perm_err = await service.update_user_permissions(
            "org-1", "u1", "u2", [OrgPermission.SETTINGS_READ.value]
        )
        self.assertTrue(update_actor_perm_err.is_err())

        service._get_member_permissions = AsyncMock(
            return_value=Ok([OrgPermission.OWNER.value])
        )
        service._ensure_user_in_org = AsyncMock(
            return_value=Err(_DummyError("target missing"))
        )
        update_target_err = await service.update_user_permissions(
            "org-1", "owner", "u2", [OrgPermission.SETTINGS_READ.value]
        )
        self.assertTrue(update_target_err.is_err())

        service._ensure_user_in_org = AsyncMock(return_value=Ok(True))
        service.kc.set_user_attribute = AsyncMock(
            return_value=Err(_DummyError("write failed"))
        )
        update_write_attr_err = await service.update_user_permissions(
            "org-1", "owner", "u2", [OrgPermission.SETTINGS_READ.value]
        )
        self.assertTrue(update_write_attr_err.is_err())
