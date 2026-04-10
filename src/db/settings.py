from src.settings import DBSettings, AppSettings


def getDBSettings():
    return AppSettings.get().db
