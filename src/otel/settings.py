from src.settings import AppSettings, ObservabilitySettings


def getOtelSettings() -> ObservabilitySettings:
    return AppSettings.get().observability
