from src.settings import AppSettings, ApiKeysSettings


def getApiKeysSettings() -> ApiKeysSettings:
    return AppSettings.get().apikey
