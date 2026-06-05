from gantry.settings import AppSettings, AuthSettings


def getAuthSettings() -> AuthSettings:
    return AppSettings.get().auth
