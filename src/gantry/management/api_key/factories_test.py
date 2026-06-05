import os
import unittest
from unittest.mock import ANY, patch


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.settings.api_key import ApiKeyPermission
from gantry.management.api_key import factories


class TestApiKeyFactories(unittest.TestCase):
    def tearDown(self):
        factories.getApiKeyService.cache_clear()
        factories.getApiKeyRepository.cache_clear()

    def test_get_api_key_service_builds_singleton(self):
        settings = type(
            "Settings",
            (),
            {
                "secret": type(
                    "Secret", (), {"get_secret_value": lambda self: "secret"}
                )(),
                "secret_length": 24,
                "permissions": [
                    ApiKeyPermission(
                        id="chat.read",
                        name="chat.read",
                        description="",
                    )
                ],
            },
        )()
        with (
            patch(
                "gantry.management.api_key.factories.getApiKeysSettings",
                return_value=settings,
            ),
            patch(
                "gantry.management.api_key.factories.getLogger",
                return_value="logger",
            ),
            patch(
                "gantry.management.api_key.factories.getSessionManager",
                return_value="session-manager",
            ),
            patch(
                "gantry.management.api_key.factories.getApiKeyRepository",
                return_value="api-key-repo",
            ),
            patch(
                "gantry.management.api_key.factories.getProjectRepository",
                return_value="project-repo",
            ),
            patch(
                "gantry.management.api_key.factories.ApiKeyService"
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
            permissions=list(settings.permissions),
            session_manager="session-manager",
            limits_storage=ANY,
        )
