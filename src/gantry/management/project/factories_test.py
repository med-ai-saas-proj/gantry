from gantry.management.project import factories

import unittest
from unittest.mock import patch


class TestProjectFactories(unittest.TestCase):
    def tearDown(self):
        factories.getProjectService.cache_clear()
        factories.getProjectRepository.cache_clear()
        factories.getProjectMemeberRepository.cache_clear()
        factories.getProjectSettingsRepository.cache_clear()

    def test_get_project_service_builds_singleton(self):
        with (
            patch(
                "gantry.management.project.factories.getSessionManager",
                return_value="session-manager",
            ),
            patch(
                "gantry.management.project.factories.getLogger",
                return_value="logger",
            ),
            patch(
                "gantry.management.project.factories.getKeycloakServiceClient",
                return_value="kc-client",
            ),
            patch(
                "gantry.management.project.factories.getProjectRepository",
                return_value="project-repo",
            ),
            patch(
                "gantry.management.project.factories.getProjectMemeberRepository",
                return_value="membership-repo",
            ),
            patch(
                "gantry.management.project.factories.getProjectSettingsRepository",
                return_value="settings-repo",
            ),
            patch(
                "gantry.management.project.factories.ProjectService"
            ) as mock_cls,
        ):
            mock_cls.return_value = "project-service"

            first = factories.getProjectService()
            second = factories.getProjectService()

        self.assertEqual(first, "project-service")
        self.assertEqual(second, "project-service")
        mock_cls.assert_called_once_with(
            session_manager="session-manager",
            logger="logger",
            project_repo="project-repo",
            membership_repo="membership-repo",
            settings_repo="settings-repo",
            kc_client="kc-client",
        )
