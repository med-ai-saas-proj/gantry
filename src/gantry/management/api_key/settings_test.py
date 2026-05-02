import os
import unittest


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.settings import AppSettings, ApiKeysSettings
from gantry.management.api_keys.settings import getApiKeysSettings


class TestApiKeySettings(unittest.TestCase):
    def test_get_api_keys_settings_reads_from_app_settings(self):
        settings = AppSettings.get()

        first = getApiKeysSettings()
        second = getApiKeysSettings()

        self.assertIsInstance(first, ApiKeysSettings)
        self.assertIs(first, second)
        self.assertIs(first, settings.apikey)
