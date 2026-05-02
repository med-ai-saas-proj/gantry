import os
import sys
import types
import unittest
from unittest.mock import patch


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.management.api_key import factories


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
        fake_billing_factories = types.ModuleType(
            "gantry.management.billing.factories"
        )
        fake_billing_factories.getBillingTransactionService = lambda: (
            "billing-transaction-service"
        )
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
                "gantry.management.api_key.factories.getRedis",
                return_value="redis-client",
            ),
            patch(
                "gantry.management.api_key.factories.ApiKeyRepository",
                return_value="api-key-repo",
            ),
            patch(
                "gantry.management.api_key.factories.ProjectRepository",
                return_value="project-repo",
            ),
            patch.dict(
                sys.modules,
                {"gantry.management.billing.factories": fake_billing_factories},
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
            session_manager="session-manager",
            billing_transaction_service="billing-transaction-service",
            redis="redis-client",
        )
