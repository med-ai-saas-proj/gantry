from src.management.organization import routes
from src.management.organization.dtos import (
    PaginatedQuery,
    InviteUserRequest,
    UpdateSettingsRequest,
    UserPermissionsRequest,
    UpdateOrgMetadataRequest,
)
from src.management.organization.permissions import ALL_PERMISSIONS

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock

from safe_result import Ok


class TestOrganizationRoutes(unittest.IsolatedAsyncioTestCase):
    async def test_metadata_and_settings_routes(self):
        service = Mock()
        info = SimpleNamespace(id="org-1", name="Org", owner_id="u1")
        delete_req = SimpleNamespace(
            org_id="org-1",
            requested_at="2026-03-17T00:00:00",
            cancel_before="2026-04-16T00:00:00",
        )
        settings = SimpleNamespace(rate_limit=10, extra={"theme": "dark"})
        service.get_org_info = AsyncMock(return_value=Ok(info))
        service.update_org_info = AsyncMock(return_value=Ok(info))
        service.request_delete_org = AsyncMock(return_value=Ok(delete_req))
        service.cancel_delete_org = AsyncMock(return_value=Ok(True))
        service.get_settings = AsyncMock(return_value=Ok(settings))
        service.update_settings = AsyncMock(return_value=Ok(settings))

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
        self.assertEqual(cancel_res.org_id, "org-1")
        self.assertTrue(cancel_res.cancelled)
        self.assertEqual(
            await routes.get_settings(user_info, "org-1", service), settings
        )
        self.assertEqual(
            await routes.update_settings(
                user_info,
                "org-1",
                UpdateSettingsRequest(rate_limit=10, extra={"theme": "dark"}),
                service,
            ),
            settings,
        )

    async def test_user_and_invitation_routes(self):
        service = Mock()
        users = SimpleNamespace(total=1, results=[])
        invitations = SimpleNamespace(results=[])
        invitation = SimpleNamespace(id="inv-1", email="a@test")
        perms = SimpleNamespace(permissions=["organization.owner"])
        service.get_users = AsyncMock(return_value=Ok(users))
        service.remove_user = AsyncMock(return_value=Ok(True))
        service.get_invitations = AsyncMock(return_value=Ok(invitations))
        service.create_invitation = AsyncMock(return_value=Ok(True))
        service.get_invitation = AsyncMock(return_value=Ok(invitation))
        service.delete_invitation = AsyncMock(return_value=Ok(True))
        service.resend_invitation = AsyncMock(return_value=Ok(True))
        service.ensure_can_read_user_permissions = AsyncMock(
            return_value=Ok(True)
        )
        service.get_user_permissions = AsyncMock(return_value=Ok(perms))
        service.update_user_permissions = AsyncMock(return_value=Ok(perms))

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
