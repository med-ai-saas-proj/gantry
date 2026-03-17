import os
import unittest

os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from src.management.auth.services import AuthService


class TestAuthService(unittest.TestCase):
    def setUp(self):
        self.service = AuthService(
            server_url="http://localhost:8080",
            realm="dev",
            client_id="med-ai-saas-app",
        )

    def test_map_claims_uses_single_organization_claim(self):
        result = self.service._mapClaimsToAuthInfo(
            {
                "sub": "user-1",
                "preferred_username": "alice",
                "email": "alice@test",
                "organization": "org-1",
                "realm_access": {"roles": ["r1"]},
                "resource_access": {
                    "med-ai-saas-app": {"roles": ["r2"]},
                    "account": {"roles": ["r3"]},
                },
                "azp": "med-ai-saas-app",
            }
        )

        self.assertTrue(result.is_ok())
        self.assertEqual(result.unwrap()["org_id"], "org-1")
        self.assertEqual(result.unwrap()["roles"], ["r1", "r2", "r3"])

    def test_map_claims_supports_multivalued_organization_claim(self):
        result = self.service._mapClaimsToAuthInfo(
            {
                "sub": "user-1",
                "preferred_username": "alice",
                "email": "alice@test",
                "organization": ["org-1", "org-2"],
                "azp": "med-ai-saas-app",
            }
        )

        self.assertTrue(result.is_ok())
        self.assertEqual(result.unwrap()["org_id"], "org-1")

    def test_map_claims_ignores_legacy_claim_names(self):
        result = self.service._mapClaimsToAuthInfo(
            {
                "sub": "user-1",
                "preferred_username": "alice",
                "email": "alice@test",
                "org_id": "legacy-org",
                "organization_id": "legacy-org-2",
                "azp": "med-ai-saas-app",
            }
        )

        self.assertTrue(result.is_ok())
        self.assertIsNone(result.unwrap()["org_id"])

    def test_map_claims_marks_service_account(self):
        result = self.service._mapClaimsToAuthInfo(
            {
                "sub": "svc-1",
                "preferred_username": "service-account-med-ai-saas-backend",
                "email": None,
                "azp": "med-ai-saas-backend",
            }
        )

        self.assertTrue(result.is_ok())
        self.assertTrue(result.unwrap()["is_service_account"])
