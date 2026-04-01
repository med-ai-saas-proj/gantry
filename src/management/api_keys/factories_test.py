import os
import unittest
from unittest.mock import patch


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from src.management.api_keys import factories


class TestApiKeyFactories(unittest.TestCase):
    def tearDown(self):
        factories.getApiKeyService.cache_clear()

    def test_get_api_key_service_builds_singleton(self):
        settings = type(
            "Settings",
            (),
            {
                "secret": type(
                    "Secret", (), {"get_secret_value": lambda self: "secret"}
                )(),
                "secret_length": 24,
            },
        )()
        with (
            patch(
                "src.management.api_keys.factories.getApiKeysSettings",
                return_value=settings,
            ),
            patch(
                "src.management.api_keys.factories.getLogger",
                return_value="logger",
            ),
            patch(
                "src.management.api_keys.factories.getSessionManager",
                return_value="session-manager",
            ),
            patch(
                "src.management.api_keys.factories.ApiKeyRepository",
                return_value="api-key-repo",
            ),
            patch(
                "src.management.api_keys.factories.ProjectRepository",
                return_value="project-repo",
            ),
            patch(
                "src.management.api_keys.factories.ApiKeyService"
            ) as service_cls,
        ):
            service_cls.return_value = "api-key-service"

            first = factories.getApiKeyService()
            second = factories.getApiKeyService()

        self.assertEqual(first, "api-key-service")
        self.assertEqual(second, "api-key-service")
        service_cls.assert_called_once_with(
            config={"key_secret": "secret", "api_key_secret_length": 24},
            logger="logger",
            api_key_repo="api-key-repo",
            project_repo="project-repo",
            session_manager="session-manager",
        )
