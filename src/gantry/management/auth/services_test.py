import os
import unittest
from unittest.mock import Mock, AsyncMock, patch

from pyrusult import ResultStatus


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.management.auth.services import (
    AuthService,
    ForbiddenError,
    MissingOrganizationClaimError,
)

from pyrusult import Ok


class TestAuthService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.keycloak_client = Mock()
        self.keycloak_client.getUserAttributes = AsyncMock(
            return_value=Ok(
                {
                    "org_permissions": ["organization.settings.read"],
                    "project_permissions": {
                        "proj-1": ["project.owner"],
                        "proj-2": ["project.settings.read"],
                    },
                }
            )
        )
        self.service = AuthService(
            server_url="http://localhost:8080",
            realm="dev",
            client_id="med-ai-saas-app",
            keycloak_client=self.keycloak_client,
        )

    async def test_map_claims_uses_single_organization_claim(self):
        result = await self.service._mapClaimsToAuthInfo(
            {
                "sub": "user-1",
                "name": "alice",
                "email": "alice@test",
                "organization": "org-1",
            }
        )

        self.assertTrue(result.status == ResultStatus.Ok)
        self.assertEqual(result.unwrap()["org_uuid"], "org-1")
        self.assertEqual(
            result.unwrap()["org_permissions"],
            ["organization.settings.read"],
        )
        self.assertEqual(
            result.unwrap()["project_permissions"],
            {
                "proj-1": ["project.owner"],
                "proj-2": ["project.settings.read"],
            },
        )

    async def test_map_claims_supports_multivalued_organization_claim(self):
        result = await self.service._mapClaimsToAuthInfo(
            {
                "sub": "user-1",
                "name": "alice",
                "email": "alice@test",
                "organization": ["org-1", "org-2"],
            }
        )

        self.assertTrue(result.status == ResultStatus.Ok)
        self.assertEqual(result.unwrap()["org_uuid"], "org-1")

    async def test_map_claims_supports_organization_claim_object_with_id(self):
        result = await self.service._mapClaimsToAuthInfo(
            {
                "sub": "user-1",
                "name": "alice",
                "email": "alice@test",
                "organization": {"demo-org": {"id": "org-1"}},
            }
        )

        self.assertTrue(result.status == ResultStatus.Ok)
        self.assertEqual(result.unwrap()["org_uuid"], "org-1")

    async def test_map_claims_rejects_missing_organization_claim(self):
        result = await self.service._mapClaimsToAuthInfo(
            {
                "sub": "user-1",
                "name": "alice",
                "email": "alice@test",
            }
        )

        self.assertTrue(result.status == ResultStatus.Err)
        self.assertIsInstance(result.err(), MissingOrganizationClaimError)

    async def test_map_claims_allows_admin_without_organization_claim(self):
        admin_service = AuthService(
            server_url="http://localhost:8080",
            realm="dev",
            client_id="gantry-admin",
            keycloak_client=self.keycloak_client,
            require_organization_claim=False,
        )

        result = await admin_service._mapClaimsToAuthInfo(
            {
                "sub": "admin-1",
                "name": "admin",
                "email": "admin@test",
            }
        )

        self.assertTrue(result.status == ResultStatus.Ok)
        self.assertEqual(result.unwrap()["org_uuid"], "")

    def test_verify_token_admin_requires_realm_admin_role(self):
        signing_key = Mock()
        signing_key.key = "secret"
        jwk_client = Mock()
        jwk_client.get_signing_key_from_jwt.return_value = signing_key

        with (
            patch.object(
                self.service, "_getJwkClient", return_value=jwk_client
            ),
            patch(
                "gantry.management.auth.services.jwt.decode",
                return_value={
                    "sub": "u1",
                    "name": "alice",
                    "email": "a@test",
                    "realm_access": {"roles": []},
                },
            ),
        ):
            result = self.service.verifyTokenAdmin("token")

        self.assertTrue(result.status == ResultStatus.Err)
        self.assertIsInstance(result.err(), ForbiddenError)

    def test_get_openid_metadata_uses_well_known_when_available(self):
        self.service._openid_client.well_known = lambda: {
            "issuer": "http://issuer.example/realms/dev",
            "jwks_uri": "http://issuer.example/certs",
        }

        self.assertEqual(
            self.service._getIssuer(),
            "http://issuer.example/realms/dev",
        )
        self.assertEqual(
            self.service._getJwksUrl(),
            "http://issuer.example/certs",
        )

    def test_get_openid_metadata_falls_back_when_well_known_fails(self):
        def raise_error():
            raise RuntimeError("boom")

        self.service._openid_client.well_known = raise_error

        self.assertEqual(
            self.service._getIssuer(),
            "http://localhost:8080/realms/dev",
        )
        self.assertEqual(
            self.service._getJwksUrl(),
            "http://localhost:8080/realms/dev/protocol/openid-connect/certs",
        )
