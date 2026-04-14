import os
import unittest


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.management.api_keys.settings import (
    ApiKeysSettings,
    getApiKeysSettings,
)


class TestApiKeySettings(unittest.TestCase):
    def tearDown(self):
        getApiKeysSettings.cache_clear()
        os.environ.pop("APIKEYS_SECRET", None)
        os.environ.pop("APIKEYS_SECRET_LENGTH", None)

    def test_get_api_keys_settings_reads_env_and_caches(self):
        os.environ["APIKEYS_SECRET"] = "top-secret"
        os.environ["APIKEYS_SECRET_LENGTH"] = "48"

        first = getApiKeysSettings()
        second = getApiKeysSettings()

        self.assertIsInstance(first, ApiKeysSettings)
        self.assertEqual(first.secret.get_secret_value(), "top-secret")
        self.assertEqual(first.secret_length, 48)
        self.assertIs(first, second)
