from pyrusult import Ok
from gantry.management.organization import routes
from gantry.management.organization.dtos import (
    PaginatedQuery,
    InviteUserRequest,
    UpdateSettingsRequest,
    UserPermissionsRequest,
    UpdateOrgMetadataRequest,
)
from gantry.management.organization.permissions import ALL_PERMISSIONS

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock


class TestOrganizationRoutes(unittest.IsolatedAsyncioTestCase):
    async def test_list_current_user_orgs_route(self):
        service = Mock()
        orgs = SimpleNamespace(total=1, results=[])
        service.listUserOrgs = AsyncMock(return_value=Ok(orgs))

        user_info = {"id": "u1", "roles": []}
        self.assertEqual(
            await routes.list_user_orgs(
                user_info,
                service,
                PaginatedQuery(limit=10, offset=5, q="clinic"),
            ),
            orgs,
        )
        service.listUserOrgs.assert_awaited_once_with(
            user_id="u1",
            limit=10,
            offset=5,
            q="clinic",
        )

    async def test_metadata_and_settings_routes(self):
        service = Mock()
        info = SimpleNamespace(org_id="org-1", name="Org", owner_id="u1")
        delete_req = SimpleNamespace(
            id="org-1",
            requested_at="2026-03-17T00:00:00",
            cancel_before="2026-04-16T00:00:00",
        )
        settings = SimpleNamespace(
            rate_limit=10,
            spending_limit=5000,
            extra={"theme": "dark"},
        )
        service.getOrgInfo = AsyncMock(return_value=Ok(info))
        service.updateOrgInfo = AsyncMock(return_value=Ok(info))
        service.requestDeleteOrg = AsyncMock(return_value=Ok(delete_req))
        service.cancelDeleteOrg = AsyncMock(return_value=Ok(True))
        service.getSettings = AsyncMock(return_value=Ok(settings))
        service.updateSettings = AsyncMock(return_value=Ok(settings))

        user_info = {"id": "u1", "roles": []}
        self.assertEqual(
            (await routes.list_org_permissions()).permissions,
            ALL_PERMISSIONS,
        )
        self.assertEqual(
            await routes.get_org_info(user_info, "org-1", service), info
        )
        self.assertEqual(
            await routes.update_org_info(
                user_info,
                "org-1",
                UpdateOrgMetadataRequest(name="New Org"),
                service,
            ),
            info,
        )
        self.assertEqual(
            await routes.delete_org(user_info, "org-1", service), delete_req
        )
        cancel_res = await routes.cancel_delete_org(user_info, "org-1", service)
        self.assertEqual(cancel_res.id, "org-1")
        self.assertTrue(cancel_res.cancelled)
        self.assertEqual(
            await routes.get_settings(user_info, "org-1", service), settings
        )
        self.assertEqual(
            await routes.update_settings(
                user_info,
                "org-1",
                UpdateSettingsRequest(
                    rate_limit=10,
                    spending_limit=5000,
                    extra={"theme": "dark"},
                ),
                service,
            ),
            settings,
        )

    async def test_user_and_invitation_routes(self):
        service = Mock()
        users = SimpleNamespace(total=1, results=[])
        invitations = SimpleNamespace(results=[])
        invitation = SimpleNamespace(
            id="inv-1",
            email="a@test",
        )
        perms = SimpleNamespace(permissions=["organization.owner"])
        service.getUsers = AsyncMock(return_value=Ok(users))
        service.removeUser = AsyncMock(return_value=Ok(True))
        service.getInvitations = AsyncMock(return_value=Ok(invitations))
        service.createInvitation = AsyncMock(return_value=Ok(True))
        service.getInvitation = AsyncMock(return_value=Ok(invitation))
        service.deleteInvitation = AsyncMock(return_value=Ok(True))
        service.resendInvitation = AsyncMock(return_value=Ok(True))
        service.ensureCanReadUserPermissions = AsyncMock(return_value=Ok(True))
        service.getUserPermissions = AsyncMock(return_value=Ok(perms))
        service.updateUserPermissions = AsyncMock(return_value=Ok(perms))

        user_info = {"id": "u1", "roles": []}
        self.assertEqual(
            await routes.get_users(
                user_info,
                "org-1",
                service,
                PaginatedQuery(limit=10, offset=0, q="abc"),
            ),
            users,
        )

        remove_response = await routes.remove_user(
            user_info, "org-1", "u2", service
        )
        self.assertEqual(remove_response.status_code, 200)

        self.assertEqual(
            await routes.get_invitations(user_info, "org-1", service),
            invitations,
        )
        invite_response = await routes.invite_user(
            user_info,
            "org-1",
            InviteUserRequest(email="a@example.com"),
            service,
        )
        self.assertEqual(invite_response.status_code, 200)
        self.assertEqual(
            await routes.get_invitation(user_info, "org-1", "inv-1", service),
            invitation,
        )
        delete_response = await routes.delete_invitation(
            user_info, "org-1", "inv-1", service
        )
        self.assertEqual(delete_response.status_code, 200)
        resend_response = await routes.resend_invitation(
            user_info, "org-1", "inv-1", service
        )
        self.assertEqual(resend_response.status_code, 200)
        self.assertEqual(
            await routes.get_user_permissions(
                user_info, "org-1", "u2", service
            ),
            perms,
        )
        self.assertEqual(
            await routes.update_user_permissions(
                user_info,
                "org-1",
                "u2",
                UserPermissionsRequest(permissions=["organization.invite"]),
                service,
            ),
            perms,
        )
