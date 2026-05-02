from gantry.management.admin import factories

import unittest
from unittest.mock import patch


class TestAdminFactories(unittest.TestCase):
    def tearDown(self):
        factories.getAdminService.cache_clear()

    def test_get_admin_service_builds_singleton(self):
        with (
            patch(
                "gantry.management.admin.factories.getSessionManager",
                return_value="session-manager",
            ),
            patch(
                "gantry.management.admin.factories.getKeycloakServiceClient",
                return_value="kc-client",
            ),
            patch(
                "gantry.management.admin.factories.getOrgService",
                return_value="org-service",
            ),
            patch(
                "gantry.management.admin.factories.getProjectService",
                return_value="project-service",
            ),
            patch(
                "gantry.management.admin.factories.getApiKeyService",
                return_value="api-key-service",
            ),
            patch(
                "gantry.management.admin.factories.ProjectRepository",
                return_value="project-repo",
            ),
            patch(
                "gantry.management.admin.factories.ApiKeyRepository",
                return_value="api-key-repo",
            ),
            patch("gantry.management.admin.factories.AdminService") as mock_cls,
        ):
            mock_cls.return_value = "admin-service"

            first = factories.getAdminService()
            second = factories.getAdminService()

        self.assertEqual(first, "admin-service")
        self.assertEqual(second, "admin-service")
        mock_cls.assert_called_once_with(
            session_manager="session-manager",
            kc_org_client="kc-client",
            org_service="org-service",
            project_service="project-service",
            apikey_service="api-key-service",
            project_repo="project-repo",
            api_key_repo="api-key-repo",
        )
