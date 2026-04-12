from gantry.settings import AppSettings, UserLogSettings


def getLoggingSettings() -> UserLogSettings:
    return AppSettings.get().user_log
