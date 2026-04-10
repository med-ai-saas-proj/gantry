from gantry.management.organization import factories

import unittest
from types import SimpleNamespace
from unittest.mock import patch


class TestOrganizationFactories(unittest.TestCase):
    def tearDown(self):
        factories.getKeycloakOrgClient.cache_clear()
        factories.getOrgService.cache_clear()

    def test_get_keycloak_org_client_builds_singleton(self):
        auth = SimpleNamespace(
            server_url=SimpleNamespace(encoded_string=lambda: "http://kc"),
            realm_name="dev",
        )
        org_settings = SimpleNamespace(
            keycloak_service_client_id="svc-id",
            keycloak_service_client_secret="svc-secret",
        )
        with (
            patch(
                "src.management.organization.factories.getAuthSettings",
                return_value=auth,
            ),
            patch(
                "src.management.organization.factories.getOrgSettings",
                return_value=org_settings,
            ),
            patch(
                "src.management.organization.factories.KeycloakOrgClient"
            ) as mock_cls,
        ):
            mock_cls.return_value = "kc-client"

            first = factories.getKeycloakOrgClient()
            second = factories.getKeycloakOrgClient()

        self.assertEqual(first, "kc-client")
        self.assertEqual(second, "kc-client")
        mock_cls.assert_called_once_with(
            server_url="http://kc",
            realm="dev",
            service_client_id="svc-id",
            service_client_secret="svc-secret",
        )

    def test_get_org_service_builds_singleton(self):
        with (
            patch(
                "src.management.organization.factories.getKeycloakOrgClient",
                return_value="kc-client",
            ),
            patch(
                "src.management.organization.factories.OrgSettingsRepository",
                return_value="settings-repo",
            ),
            patch(
                "src.management.organization.factories.OrgDeletionRequestRepository",
                return_value="deletion-repo",
            ),
            patch(
                "src.management.organization.factories.getSessionManager",
                return_value="session-manager",
            ),
            patch(
                "src.management.organization.factories.getLogger",
                return_value="logger",
            ),
            patch(
                "src.management.organization.factories.OrgService"
            ) as mock_cls,
        ):
            mock_cls.return_value = "org-service"

            first = factories.getOrgService()
            second = factories.getOrgService()

        self.assertEqual(first, "org-service")
        self.assertEqual(second, "org-service")
        mock_cls.assert_called_once_with(
            kc_client="kc-client",
            settings_repo="settings-repo",
            deletion_repo="deletion-repo",
            session_manager="session-manager",
            logger="logger",
        )
