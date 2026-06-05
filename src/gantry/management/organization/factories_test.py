from gantry.management.organization import factories

import unittest
from unittest.mock import patch


class TestOrganizationFactories(unittest.TestCase):
    def tearDown(self):
        factories.getOrgSettingsRepository.cache_clear()
        factories.getOrgService.cache_clear()

    def test_get_org_settings_repository_builds_singleton(self):
        with (
            patch(
                "gantry.management.organization.factories.getRedisCacheRepo",
                return_value="cache-repo",
            ),
            patch(
                "gantry.management.organization.factories.OrgSettingsRepository"
            ) as repo_cls,
        ):
            repo_cls.return_value = "settings-repo"

            first = factories.getOrgSettingsRepository()
            second = factories.getOrgSettingsRepository()

        self.assertEqual(first, "settings-repo")
        self.assertEqual(second, "settings-repo")
        repo_cls.assert_called_once_with("cache-repo")

    def test_get_org_service_builds_singleton(self):
        with (
            patch(
                "gantry.management.organization.factories.getKeycloakServiceClient",
                return_value="kc-client",
            ),
            patch(
                "gantry.management.organization.factories.getOrgSettingsRepository",
                return_value="settings-repo",
            ),
            patch(
                "gantry.management.organization.factories.getOrgDeletionRequestRepository",
                return_value="deletion-repo",
            ),
            patch(
                "gantry.management.organization.factories.getSessionManager",
                return_value="session-manager",
            ),
            patch(
                "gantry.management.organization.factories.getLogger",
                return_value="logger",
            ),
            patch(
                "gantry.management.organization.factories.OrgService"
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
