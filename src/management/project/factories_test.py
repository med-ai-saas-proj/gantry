from src.management.project import factories

import unittest
from unittest.mock import patch


class TestProjectFactories(unittest.TestCase):
    def tearDown(self):
        factories.getProjectService.cache_clear()

    def test_get_project_service_builds_singleton(self):
        with (
            patch(
                "src.management.project.factories.getSessionManager",
                return_value="session-manager",
            ),
            patch(
                "src.management.project.factories.getLogger",
                return_value="logger",
            ),
            patch(
                "src.management.project.factories.getKeycloakOrgClient",
                return_value="kc-client",
            ),
            patch(
                "src.management.project.factories.ProjectRepository",
                return_value="project-repo",
            ),
            patch(
                "src.management.project.factories.ProjectMemberRepository",
                return_value="membership-repo",
            ),
            patch(
                "src.management.project.factories.ProjectService"
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
            kc_client="kc-client",
        )
