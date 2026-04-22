import os
import unittest

from pyrusult import ResultStatus


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.management.auth.services import (
    AuthService,
    MissingOrganizationClaimError,
)


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
                "project_permissions": [
                    "proj-1:project.owner",
                    "proj-2:project.settings.read",
                ],
                "realm_access": {"roles": ["r1"]},
                "resource_access": {
                    "med-ai-saas-app": {"roles": ["r2"]},
                    "account": {"roles": ["r3"]},
                },
                "azp": "med-ai-saas-app",
            }
        )

        self.assertTrue(result.status == ResultStatus.Ok)
        self.assertEqual(result.unwrap()["org_id"], "org-1")
        self.assertEqual(result.unwrap()["roles"], ["r1", "r2", "r3"])
        self.assertEqual(result.unwrap()["project_ids"], ["proj-1", "proj-2"])

    def test_map_claims_extracts_project_ids_from_role_entries(self):
        result = self.service._mapClaimsToAuthInfo(
            {
                "sub": "user-1",
                "preferred_username": "alice",
                "email": "alice@test",
                "organization": "org-1",
                "realm_access": {
                    "roles": [
                        "proj-1:project.owner",
                        "proj-2:project.settings.read",
                        "not-a-project-role",
                    ]
                },
                "azp": "med-ai-saas-app",
            }
        )

        self.assertTrue(result.status == ResultStatus.Ok)
        self.assertEqual(result.unwrap()["project_ids"], ["proj-1", "proj-2"])

    def test_map_claims_deduplicates_project_ids(self):
        result = self.service._mapClaimsToAuthInfo(
            {
                "sub": "user-1",
                "preferred_username": "alice",
                "email": "alice@test",
                "organization": "org-1",
                "project_permissions": [
                    "proj-1:project.owner",
                    "proj-1:project.settings.write",
                ],
                "azp": "med-ai-saas-app",
            }
        )

        self.assertTrue(result.status == ResultStatus.Ok)
        self.assertEqual(result.unwrap()["project_ids"], ["proj-1"])

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

        self.assertTrue(result.status == ResultStatus.Ok)
        self.assertEqual(result.unwrap()["org_id"], "org-1")

    def test_map_claims_supports_organization_claim_object_with_id(self):
        result = self.service._mapClaimsToAuthInfo(
            {
                "sub": "user-1",
                "preferred_username": "alice",
                "email": "alice@test",
                "organization": {
                    "demo-org": {"id": "org-1"},
                },
                "azp": "med-ai-saas-app",
            }
        )

        self.assertTrue(result.status == ResultStatus.Ok)
        self.assertEqual(result.unwrap()["org_id"], "org-1")

    def test_map_claims_rejects_organization_claim_object_without_id(self):
        result = self.service._mapClaimsToAuthInfo(
            {
                "sub": "user-1",
                "preferred_username": "alice",
                "email": "alice@test",
                "organization": {
                    "demo-org": {"name": "demo-org"},
                },
                "azp": "med-ai-saas-app",
            }
        )

        self.assertTrue(result.status == ResultStatus.Err)
        self.assertIsInstance(result.err(), MissingOrganizationClaimError)

    def test_map_claims_rejects_regular_user_without_organization_claim(self):
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

        self.assertTrue(result.status == ResultStatus.Err)
        self.assertIsInstance(result.err(), MissingOrganizationClaimError)

    def test_map_claims_rejects_missing_organization_claim(self):
        result = self.service._mapClaimsToAuthInfo(
            {
                "sub": "svc-1",
                "preferred_username": "service-account-med-ai-saas-backend",
                "email": None,
                "azp": "med-ai-saas-backend",
            }
        )

        self.assertTrue(result.status == ResultStatus.Err)
        self.assertIsInstance(result.err(), MissingOrganizationClaimError)
