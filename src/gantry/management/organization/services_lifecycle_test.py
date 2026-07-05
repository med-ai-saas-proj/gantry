"""Category tests for organization service unit rules."""

from .services_test_support import (
    UTC,
    Ok,
    Err,
    AsyncMock,
    ResultStatus,
    OrgPermission,
    SimpleNamespace,
    OrgNotFoundError,
    BaseOrgServiceTest,
    MemberNotFoundError,
    OwnerRemovalNotAllowedError,
    DeletionRequestNotFoundError,
    OwnerPermissionRequiredError,
    DeletionAlreadyRequestedError,
    UserAlreadyInAnotherOrganizationError,
    datetime,
    _DummyError,
)


class TestOrgServiceLifecycle(BaseOrgServiceTest):
    """Organization service tests grouped by category."""

    async def test_create_org_with_owner_seeds_owner_when_user_has_no_org(self):
        """Creating an org can seed the first owner when user is unassigned."""
        service = self._make_service()
        service.kc.getMemberOrganizations = AsyncMock(return_value=Ok([]))
        service.kc.createOrg = AsyncMock(return_value=Ok("org-1"))
        service.kc.addMember = AsyncMock(return_value=Ok(True))
        service.kc.setUserAttribute = AsyncMock(return_value=Ok(True))

        res = await service.createOrg(
            name="Org 1",
            alias="org-1",
            owner_id="user-1",
        )

        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().owner_id, "user-1")
        service.kc.getMemberOrganizations.assert_awaited_once_with("user-1")
        service.kc.createOrg.assert_awaited_once_with(
            {"name": "Org 1", "alias": "org-1"}
        )
        service.kc.addMember.assert_awaited_once_with("org-1", "user-1")
        service.kc.setUserAttribute.assert_awaited_once_with(
            "user-1",
            "org_permissions",
            [OrgPermission.OWNER.value],
        )

    async def test_create_org_rejects_owner_already_in_another_org(self):
        """Owner seeding must preserve the one-user-one-org invariant."""
        service = self._make_service()
        service.kc.getMemberOrganizations = AsyncMock(
            return_value=Ok([{"id": "org-2", "name": "Other"}])
        )
        service.kc.createOrg = AsyncMock()

        res = await service.createOrg(
            name="Org 1",
            alias="org-1",
            owner_id="user-1",
        )

        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), UserAlreadyInAnotherOrganizationError)
        service.kc.createOrg.assert_not_awaited()

    async def test_create_org_for_user_seeds_current_user_as_owner(self):
        """Self-service org creation should make the creator the owner."""
        service = self._make_service()
        service.kc.getMemberOrganizations = AsyncMock(return_value=Ok([]))
        service.kc.createOrg = AsyncMock(return_value=Ok("org-1"))
        service.kc.addMember = AsyncMock(return_value=Ok(True))
        service.kc.setUserAttribute = AsyncMock(return_value=Ok(True))

        res = await service.createOrgForUser(
            user_id="user-1",
            name="Org 1",
            alias="org-1",
        )

        self.assertTrue(res.status == ResultStatus.Ok)
        payload = res.unwrap()
        self.assertEqual(payload.org_id, "org-1")
        self.assertEqual(payload.owner_id, "user-1")
        service.kc.getMemberOrganizations.assert_awaited_once_with("user-1")
        service.kc.addMember.assert_awaited_once_with("org-1", "user-1")
        service.kc.setUserAttribute.assert_awaited_once_with(
            "user-1",
            "org_permissions",
            [OrgPermission.OWNER.value],
        )

    async def test_remove_owner_not_allowed(self):
        """Organization owner removal should be blocked."""
        # Arrange
        service = self._make_service()
        service._getOrgOwnerId = AsyncMock(return_value=Ok("owner"))

        # Act
        res = await service.removeUser("org-1", "owner")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), OwnerRemovalNotAllowedError)

    async def test_request_delete_org_conflict_when_already_requested(self):
        """Requesting deletion twice should return conflict."""
        # Arrange
        service = self._make_service()
        service._ensureOrgExists = AsyncMock(return_value=Ok({"id": "org-1"}))
        service.deletion_repo.getByOrgId = AsyncMock(
            return_value=SimpleNamespace(id=1)
        )

        # Act
        res = await service.requestDeleteOrg("org-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), DeletionAlreadyRequestedError)

    async def test_list_user_orgs_filters_and_paginates_member_orgs(self):
        """User org search should stay scoped to the user's memberships."""
        # Arrange
        service = self._make_service()
        service.kc.getMemberOrganizations = AsyncMock(
            return_value=Ok(
                [
                    {"id": "org-1", "name": "Cardiology", "alias": "heart"},
                    {"id": "org-2", "name": "Dental", "alias": "clinic"},
                    {"id": "org-3", "name": "Clinic Ops", "alias": "ops"},
                ]
            )
        )

        # Act
        res = await service.listUserOrgs(
            user_id="user-1",
            limit=1,
            offset=1,
            q="clinic",
        )

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        payload = res.unwrap()
        self.assertEqual(payload.total, 2)
        self.assertEqual(len(payload.results), 1)
        self.assertEqual(payload.results[0].org_id, "org-3")
        service.kc.getMemberOrganizations.assert_awaited_once_with("user-1")

    async def test_list_orgs_enriches_owner_and_deletion_metadata(self):
        """Admin org overview should show owners and pending delete metadata."""
        service = self._make_service()
        requested_at = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        service.kc.listOrgs = AsyncMock(
            return_value=Ok(
                [
                    {"id": "org-1", "name": "Active Org"},
                    {"id": "org-2", "name": "Deleting Org"},
                ]
            )
        )
        service.deletion_repo.getByOrgId = AsyncMock(
            side_effect=[
                None,
                SimpleNamespace(id=1, requested_at=requested_at),
            ]
        )
        service._getOrgOwnerId = AsyncMock(return_value=Ok("owner-1"))

        res = await service.listOrgs(limit=10, offset=0, q=None)

        self.assertTrue(res.status == ResultStatus.Ok)
        payload = res.unwrap()
        self.assertEqual(payload.total, 2)
        self.assertEqual(payload.results[0].org_id, "org-1")
        self.assertEqual(payload.results[0].owner_id, "owner-1")
        self.assertIsNone(payload.results[0].requested_at)
        self.assertIsNone(payload.results[0].delete_at)
        self.assertEqual(payload.results[1].org_id, "org-2")
        self.assertEqual(payload.results[1].owner_id, "owner-1")
        self.assertEqual(
            payload.results[1].requested_at,
            "2026-01-01T00:00:00+00:00",
        )
        self.assertEqual(
            payload.results[1].delete_at,
            "2026-01-31T00:00:00+00:00",
        )
        self.assertEqual(service._getOrgOwnerId.await_count, 2)

    async def test_request_delete_org_success(self):
        """Deletion request should return timestamps and commit."""
        # Arrange
        service = self._make_service()
        now = datetime(2026, 3, 13, 10, 0, tzinfo=UTC).replace(tzinfo=None)
        service._ensureOrgExists = AsyncMock(return_value=Ok({"id": "org-1"}))
        service.deletion_repo.getByOrgId = AsyncMock(return_value=None)
        service.deletion_repo.upsertRequest = AsyncMock(
            return_value=SimpleNamespace(requested_at=now)
        )

        # Act
        res = await service.requestDeleteOrg("org-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().id, "org-1")
        self.session_manager.session.commit.assert_awaited()

    async def test_cancel_delete_org_not_found(self):
        """Cancel should fail if there is no pending deletion request."""
        # Arrange
        service = self._make_service()
        service.deletion_repo.deleteByOrgId = AsyncMock(return_value=False)

        # Act
        res = await service.cancelDeleteOrg("org-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), DeletionRequestNotFoundError)

    async def test_cancel_delete_org_success(self):
        """Cancel should delete pending request and commit."""
        # Arrange
        service = self._make_service()
        service.deletion_repo.deleteByOrgId = AsyncMock(return_value=True)

        # Act
        res = await service.cancelDeleteOrg("org-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertTrue(res.unwrap())
        self.session_manager.session.commit.assert_awaited()

    async def test_update_org_info_requires_owner_for_non_owner_actor(self):
        """Non-owner actor cannot update org metadata."""
        # Arrange
        service = self._make_service()
        service._getOrgOwnerId = AsyncMock(return_value=Ok("u-owner"))

        # Act
        res = await service.updateOrgInfo(
            org_id="org-1",
            actor_user_id="u-not-owner",
            name="new-name",
        )

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), OwnerPermissionRequiredError)

    async def test_update_org_info_requires_owner(self):
        """Non-owner should not be able to update organization metadata."""
        # Arrange
        service = self._make_service()
        service._getOrgOwnerId = AsyncMock(return_value=Ok("u-owner"))

        # Act
        res = await service.updateOrgInfo(
            org_id="org-1",
            actor_user_id="u-other",
            name="new-name",
        )

        # Assert
        self.assertTrue(res.status == ResultStatus.Err)
        self.assertIsInstance(res.err(), OwnerPermissionRequiredError)

    async def test_update_org_info_owner_success(self):
        """Organization owner should be able to rename the organization."""
        # Arrange
        service = self._make_service()
        service._getOrgOwnerId = AsyncMock(return_value=Ok("u-owner"))
        service.kc.getOrg = AsyncMock(
            return_value=Ok({"id": "org-1", "name": "old-name"})
        )
        service.kc.updateOrg = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.updateOrgInfo(
            org_id="org-1",
            actor_user_id="u-owner",
            name="new-name",
        )

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().owner_id, "u-owner")

    async def test_get_org_info_without_owner_returns_owner_id_none(self):
        """Org info should still resolve when no owner attribute exists yet."""
        # Arrange
        service = self._make_service()
        service.kc.getOrg = AsyncMock(
            return_value=Ok({"id": "org-1", "name": "Org One"})
        )
        from gantry.management.organization.services import OwnerNotFoundError

        service._getOrgOwnerId = AsyncMock(
            return_value=Err(OwnerNotFoundError())
        )

        # Act
        res = await service.getOrgInfo("org-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertIsNone(res.unwrap().owner_id)

    async def test_get_org_info_with_owner_success(self):
        """Org info should include resolved owner id when exactly one owner exists."""
        # Arrange
        service = self._make_service()
        service.kc.getOrg = AsyncMock(
            return_value=Ok({"id": "org-1", "name": "Org One"})
        )
        service._getOrgOwnerId = AsyncMock(return_value=Ok("u1"))

        # Act
        res = await service.getOrgInfo("org-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().owner_id, "u1")

    async def test_get_settings_success(self):
        """Get settings should return repository values and commit session."""
        # Arrange
        service = self._make_service()
        service._ensureOrgExists = AsyncMock(return_value=Ok({"id": "org-1"}))
        service.settings_repo.getOrCreate = AsyncMock(
            return_value=SimpleNamespace(
                rate_limit=100,
                spending_limit=5000,
                extra={"a": 1},
            )
        )

        # Act
        res = await service.getSettings("org-1")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().rate_limit, 100)
        self.assertEqual(res.unwrap().spending_limit, 5000)
        self.assertEqual(res.unwrap().extra, {"a": 1})

    async def test_process_due_deletions_deletes_org_and_cleans_records(self):
        """Deletion worker should delete due orgs and clean DB records."""
        # Arrange
        service = self._make_service()
        due_request = SimpleNamespace(org_id="org-1")
        service.deletion_repo.listDueRequests = AsyncMock(
            return_value=[due_request]
        )
        service.kc.deleteOrg = AsyncMock(return_value=Ok(True))
        service.settings_repo.deleteByOrgId = AsyncMock(return_value=True)
        service.deletion_repo.deleteByOrgId = AsyncMock(return_value=True)

        # Act
        processed = await service.processDueDeletions(batch_size=10)

        # Assert
        self.assertEqual(processed, 1)
        service.kc.deleteOrg.assert_awaited_once_with("org-1")
        service.settings_repo.deleteByOrgId.assert_awaited_once()
        self.session_manager.session.commit.assert_awaited()

    async def test_process_due_deletions_skips_failed_keycloak_delete(self):
        """Deletion worker should continue when Keycloak deletion fails."""
        # Arrange
        service = self._make_service()
        due_request = SimpleNamespace(org_id="org-1")
        service.deletion_repo.listDueRequests = AsyncMock(
            return_value=[due_request]
        )
        service.kc.deleteOrg = AsyncMock(
            return_value=Err(DeletionAlreadyRequestedError())
        )
        service.settings_repo.deleteByOrgId = AsyncMock()
        service.deletion_repo.deleteByOrgId = AsyncMock()

        # Act
        processed = await service.processDueDeletions(batch_size=10)

        # Assert
        self.assertEqual(processed, 0)
        service.settings_repo.deleteByOrgId.assert_not_called()
        service.deletion_repo.deleteByOrgId.assert_not_called()

    async def test_process_due_deletions_treats_missing_org_as_processed(self):
        """Deletion worker should still cleanup local records if org is already gone."""
        # Arrange
        service = self._make_service()
        due_request = SimpleNamespace(org_id="org-1")
        service.deletion_repo.listDueRequests = AsyncMock(
            return_value=[due_request]
        )
        service.kc.deleteOrg = AsyncMock(return_value=Err(OrgNotFoundError()))
        service.settings_repo.deleteByOrgId = AsyncMock(return_value=True)
        service.deletion_repo.deleteByOrgId = AsyncMock(return_value=True)

        # Act
        processed = await service.processDueDeletions(batch_size=10)

        # Assert
        self.assertEqual(processed, 1)
        service.settings_repo.deleteByOrgId.assert_awaited_once_with(
            self.session_manager.session, "org-1"
        )

    async def test_get_users_falls_back_to_member_count_when_count_fails(self):
        """User listing should fall back to page length if count lookup fails."""
        # Arrange
        service = self._make_service()
        service.kc.getOrgMembers = AsyncMock(
            return_value=Ok(
                [
                    {"id": "u1", "username": "one", "email": "1@test"},
                    {"id": "u2", "username": "two", "email": "2@test"},
                ]
            )
        )
        service.kc.getOrgMemberCount = AsyncMock(
            return_value=Err(OrgNotFoundError())
        )

        # Act
        res = await service.getUsers("org-1", limit=20, offset=0)

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().total, 2)

    async def test_remove_user_success_deletes_member_record_and_user(self):
        """Removing non-owner user should remove org membership then delete user."""
        # Arrange
        service = self._make_service()
        service._getOrgOwnerId = AsyncMock(return_value=Ok("owner"))
        service.kc.removeMember = AsyncMock(return_value=Ok(True))
        service.kc.deleteUser = AsyncMock(return_value=Ok(True))

        # Act
        res = await service.removeUser("org-1", "u-member")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        service.kc.removeMember.assert_awaited_once_with("org-1", "u-member")
        service.kc.deleteUser.assert_awaited_once_with("u-member")

    async def test_remove_user_succeeds_when_account_is_already_deleted(self):
        """Removing membership is enough when Keycloak user deletion is already done."""
        # Arrange
        service = self._make_service()
        service._getOrgOwnerId = AsyncMock(return_value=Ok("owner"))
        service.kc.removeMember = AsyncMock(return_value=Ok(True))
        service.kc.deleteUser = AsyncMock(
            return_value=Err(MemberNotFoundError())
        )

        # Act
        res = await service.removeUser("org-1", "u-member")

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertTrue(res.unwrap())
        service.kc.removeMember.assert_awaited_once_with("org-1", "u-member")
        service.kc.deleteUser.assert_awaited_once_with("u-member")

    async def test_update_settings_flattens_nested_extra(self):
        """Update settings should flatten nested extra keys before upsert."""
        # Arrange
        service = self._make_service()
        service._ensureOrgExists = AsyncMock(return_value=Ok({"id": "org-1"}))
        service.settings_repo.upsert = AsyncMock(
            return_value=SimpleNamespace(
                rate_limit=90,
                spending_limit=7000,
                extra={"a.b": 1, "x": 2},
            )
        )

        # Act
        res = await service.updateSettings(
            org_id="org-1",
            rate_limit=90,
            spending_limit=7000,
            extra={"a": {"b": 1}, "x": 2},
        )

        # Assert
        self.assertTrue(res.status == ResultStatus.Ok)
        self.assertEqual(res.unwrap().spending_limit, 7000)
        self.assertEqual(res.unwrap().extra, {"a.b": 1, "x": 2})
        service.settings_repo.upsert.assert_awaited_once()

    async def test_misc_org_error_propagation_paths(self):
        """Org service should propagate upstream collaborator errors on edge paths."""
        # Arrange
        service = self._make_service()
        service.kc.getOrg = AsyncMock(return_value=Ok({"id": "org-1"}))

        # _ensure_user_in_org -> kc lookup error
        service.kc.getMemberOrganizations = AsyncMock(
            return_value=Err(_DummyError("org lookup failed"))
        )
        ensure_err = await service._ensureUserInOrg("org-1", "u1")
        self.assertTrue(ensure_err.status == ResultStatus.Err)

        # _get_member_permissions -> attribute error
        service._ensureUserInOrg = AsyncMock(return_value=Ok(True))
        service.kc.getUserAttributes = AsyncMock(
            return_value=Err(_DummyError("attr failed"))
        )
        member_perm_err = await service._getMemberPermissions("org-1", "u1")
        self.assertTrue(member_perm_err.status == ResultStatus.Err)

        # _get_org_owner_id -> member page error, skip blank ids, attr error
        service.kc.getOrgMembers = AsyncMock(
            return_value=Err(_DummyError("member page failed"))
        )
        owner_page_err = await service._getOrgOwnerId("org-1")
        self.assertTrue(owner_page_err.status == ResultStatus.Err)

        service.kc.getOrgMembers = AsyncMock(
            side_effect=[
                Ok([{"id": ""}, {"id": "u1"}]),
                Ok([]),
            ]
        )
        service.kc.getUserAttributes = AsyncMock(
            return_value=Err(_DummyError("owner attr failed"))
        )
        owner_attr_err = await service._getOrgOwnerId("org-1")
        self.assertTrue(owner_attr_err.status == ResultStatus.Err)

        # _sync_metadata_from_keycloak -> org error and owner error
        service.kc.getOrg = AsyncMock(
            return_value=Err(_DummyError("org failed"))
        )
        org_info_err = await service.getOrgInfo("org-1")
        self.assertTrue(org_info_err.status == ResultStatus.Err)

        service.kc.getOrg = AsyncMock(return_value=Ok({"id": "org-1"}))
        service._getOrgOwnerId = AsyncMock(
            return_value=Err(_DummyError("owner failed"))
        )
        owner_info_err = await service.getOrgInfo("org-1")
        self.assertTrue(owner_info_err.status == ResultStatus.Err)

        # request_delete_org/get_settings/update_settings -> org not found
        service._ensureOrgExists = AsyncMock(
            return_value=Err(OrgNotFoundError())
        )
        delete_req_err = await service.requestDeleteOrg("org-1")
        get_settings_err = await service.getSettings("org-1")
        update_settings_err = await service.updateSettings(
            "org-1", 10, None, {}
        )
        self.assertTrue(delete_req_err.status == ResultStatus.Err)
        self.assertTrue(get_settings_err.status == ResultStatus.Err)
        self.assertTrue(update_settings_err.status == ResultStatus.Err)

        # update_org_info -> owner lookup error, get_org error, update_org error
        service._getOrgOwnerId = AsyncMock(
            return_value=Err(_DummyError("owner lookup failed"))
        )
        update_owner_err = await service.updateOrgInfo(
            "org-1", "u1", "new-name"
        )
        self.assertTrue(update_owner_err.status == ResultStatus.Err)

        service._getOrgOwnerId = AsyncMock(return_value=Ok("u1"))
        service.kc.getOrg = AsyncMock(
            return_value=Err(_DummyError("org failed"))
        )
        update_get_org_err = await service.updateOrgInfo(
            "org-1", "u1", "new-name"
        )
        self.assertTrue(update_get_org_err.status == ResultStatus.Err)

        service.kc.getOrg = AsyncMock(return_value=Ok({"id": "org-1"}))
        service.kc.updateOrg = AsyncMock(
            return_value=Err(_DummyError("update failed"))
        )
        update_write_err = await service.updateOrgInfo(
            "org-1", "u1", "new-name"
        )
        self.assertTrue(update_write_err.status == ResultStatus.Err)

        # get_users/remove_user/invitation read+write paths
        service.kc.getOrgMembers = AsyncMock(
            return_value=Err(_DummyError("get members failed"))
        )
        users_err = await service.getUsers("org-1")
        self.assertTrue(users_err.status == ResultStatus.Err)

        service._getOrgOwnerId = AsyncMock(
            return_value=Err(_DummyError("owner remove failed"))
        )
        remove_owner_err = await service.removeUser("org-1", "u2")
        self.assertTrue(remove_owner_err.status == ResultStatus.Err)

        service._getOrgOwnerId = AsyncMock(return_value=Ok("owner"))
        service.kc.removeMember = AsyncMock(
            return_value=Err(_DummyError("remove failed"))
        )
        remove_member_err = await service.removeUser("org-1", "u2")
        self.assertTrue(remove_member_err.status == ResultStatus.Err)

        service.kc.getInvitations = AsyncMock(
            return_value=Err(_DummyError("list invites failed"))
        )
        service.kc.getInvitation = AsyncMock(
            return_value=Err(_DummyError("get invite failed"))
        )
        self.assertTrue(
            (await service.getInvitations("org-1")).status == ResultStatus.Err
        )
        self.assertTrue(
            (await service.getInvitation("org-1", "inv-1")).status
            == ResultStatus.Err
        )

        service.kc.findUserByEmail = AsyncMock(
            return_value=Err(_DummyError("find failed"))
        )
        self.assertTrue(
            (await service.createInvitation("org-1", "a@test")).status
            == ResultStatus.Err
        )

        service.kc.findUserByEmail = AsyncMock(return_value=Ok({"id": "u1"}))
        service.kc.getMemberOrganizations = AsyncMock(
            return_value=Err(_DummyError("member orgs failed"))
        )
        self.assertTrue(
            (await service.createInvitation("org-1", "a@test")).status
            == ResultStatus.Err
        )

        service.kc.findUserByEmail = AsyncMock(return_value=Ok(None))
        service.kc.inviteUser = AsyncMock(
            return_value=Err(_DummyError("invite failed"))
        )
        self.assertTrue(
            (await service.createInvitation("org-1", "a@test")).status
            == ResultStatus.Err
        )

        # ensure_can_read/update_user_permissions -> target/actor/write errors
        service._ensureUserInOrg = AsyncMock(
            return_value=Err(_DummyError("target missing"))
        )
        read_target_err = await service.ensureCanReadUserPermissions(
            "org-1", "u1", "u2"
        )
        self.assertTrue(read_target_err.status == ResultStatus.Err)

        service._ensureUserInOrg = AsyncMock(return_value=Ok(True))
        service._getMemberPermissions = AsyncMock(
            return_value=Err(_DummyError("actor perms failed"))
        )
        read_actor_err = await service.ensureCanReadUserPermissions(
            "org-1", "u1", "u2"
        )
        self.assertTrue(read_actor_err.status == ResultStatus.Err)

        service._getOrgOwnerId = AsyncMock(
            return_value=Err(_DummyError("owner failed"))
        )
        update_owner_lookup_err = await service.updateUserPermissions(
            "org-1", "u1", "u2", [OrgPermission.SETTINGS_READ.value]
        )
        self.assertTrue(update_owner_lookup_err.status == ResultStatus.Err)

        service._getOrgOwnerId = AsyncMock(return_value=Ok("owner"))
        service._getMemberPermissions = AsyncMock(
            return_value=Err(_DummyError("actor perms failed"))
        )
        update_actor_perm_err = await service.updateUserPermissions(
            "org-1", "u1", "u2", [OrgPermission.SETTINGS_READ.value]
        )
        self.assertTrue(update_actor_perm_err.status == ResultStatus.Err)

        service._getMemberPermissions = AsyncMock(
            return_value=Ok([OrgPermission.OWNER.value])
        )
        service._ensureUserInOrg = AsyncMock(
            return_value=Err(_DummyError("target missing"))
        )
        update_target_err = await service.updateUserPermissions(
            "org-1", "owner", "u2", [OrgPermission.SETTINGS_READ.value]
        )
        self.assertTrue(update_target_err.status == ResultStatus.Err)

        service._ensureUserInOrg = AsyncMock(return_value=Ok(True))
        service.kc.setUserAttribute = AsyncMock(
            return_value=Err(_DummyError("write failed"))
        )
        update_write_attr_err = await service.updateUserPermissions(
            "org-1", "owner", "u2", [OrgPermission.SETTINGS_READ.value]
        )
        self.assertTrue(update_write_attr_err.status == ResultStatus.Err)
