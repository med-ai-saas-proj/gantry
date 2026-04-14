from gantry.settings import AppSettings, OrgSettings


def getOrgSettings() -> OrgSettings:
    return AppSettings.get().organization
