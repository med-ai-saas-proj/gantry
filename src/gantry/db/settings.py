from gantry.settings import DBSettings, AppSettings


def getDBSettings():
    return AppSettings.get().db
