import os
import unittest
from unittest.mock import Mock, AsyncMock

from pyrusult import Ok, Err


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.management.auth.services import MissingOrganizationClaimError
from gantry.management.auth.dependencies import (
    MissingOrganizationContextError,
    getUserInfo,
    getUserOrgId,
    requireUserOrgId,
)


class _DummyErr(Exception):
    pass


class TestAuthDependencies(unittest.IsolatedAsyncioTestCase):
    async def test_get_user_info_resolves_claim_org_id_from_memberships(self):
        auth_service = Mock()
        project_service = Mock()
        project_service.listAccessibleProjects = AsyncMock(
            return_value=Ok(
                Mock(
                    results=[
                        Mock(
                            id="proj-1",
                            name="Project 1",
                            description="desc",
                            organization_id=(
                                "11111111-1111-1111-1111-111111111111"
                            ),
                            archived=False,
                        )
                    ]
                )
            )
        )
        auth_service.verifyToken.return_value = Ok(
            {
                "id": "u1",
                "username": "alice",
                "email": "a@test",
                "roles": [],
                "org_id": "11111111-1111-1111-1111-111111111111",
            }
        )
        kc_org_client = Mock()
        kc_org_client.getMemberOrganizations = AsyncMock(
            return_value=Ok(
                [
                    {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "name": "org-name",
                        "alias": "org-alias",
                    }
                ]
            )
        )

        user_info = await getUserInfo(
            "token",
            auth_service,
            kc_org_client,
            project_service,
        )

        self.assertEqual(
            user_info["org_id"], "11111111-1111-1111-1111-111111111111"
        )
        self.assertEqual(user_info["projects"][0]["id"], "proj-1")
        kc_org_client.getMemberOrganizations.assert_awaited_once_with("u1")
        project_service.listAccessibleProjects.assert_awaited_once_with(
            actor_user_id="u1",
            organization_id="11111111-1111-1111-1111-111111111111",
        )

    async def test_get_user_info_resolves_org_name_claim_to_org_id(self):
        auth_service = Mock()
        project_service = Mock()
        project_service.listAccessibleProjects = AsyncMock(
            return_value=Ok(Mock(results=[]))
        )
        auth_service.verifyToken.return_value = Ok(
            {
                "id": "u1",
                "username": "alice",
                "email": "a@test",
                "roles": [],
                "org_id": "org-name",
            }
        )
        kc_org_client = Mock()
        kc_org_client.getMemberOrganizations = AsyncMock(
            return_value=Ok(
                [{"id": "org-1", "name": "org-name", "alias": "org-alias"}]
            )
        )

        user_info = await getUserInfo(
            "token",
            auth_service,
            kc_org_client,
            project_service,
        )

        self.assertEqual(user_info["org_id"], "org-1")
        self.assertEqual(user_info["projects"], [])

    async def test_get_user_info_rejects_regular_user_without_org(self):
        auth_service = Mock()
        auth_service.verifyToken.return_value = Err(
            MissingOrganizationClaimError()
        )
        kc_org_client = Mock()
        project_service = Mock()

        with self.assertRaises(MissingOrganizationClaimError):
            await getUserInfo(
                "token",
                auth_service,
                kc_org_client,
                project_service,
            )

    async def test_get_user_info_falls_back_to_empty_projects_on_lookup_error(
        self,
    ):
        auth_service = Mock()
        project_service = Mock()
        project_service.listAccessibleProjects = AsyncMock(
            return_value=Err(_DummyErr("lookup failed"))
        )
        auth_service.verifyToken.return_value = Ok(
            {
                "id": "u1",
                "username": "alice",
                "email": "a@test",
                "roles": [],
                "org_id": "org-1",
            }
        )
        kc_org_client = Mock()
        kc_org_client.getMemberOrganizations = AsyncMock(
            return_value=Ok([{"id": "org-1", "name": "org-name"}])
        )

        user_info = await getUserInfo(
            "token",
            auth_service,
            kc_org_client,
            project_service,
        )

        self.assertEqual(user_info["projects"], [])

    async def test_get_user_org_id_and_require_user_org_id(self):
        self.assertEqual(
            await getUserOrgId({"id": "u1", "roles": [], "org_id": "org-1"}),
            "org-1",
        )
        self.assertEqual(await requireUserOrgId("org-1"), "org-1")
        with self.assertRaises(MissingOrganizationContextError):
            await requireUserOrgId("")
