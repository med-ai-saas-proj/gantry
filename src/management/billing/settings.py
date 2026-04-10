from src.settings import AppSettings, BillingSourceSettings


def getBillingSourceSetting() -> BillingSourceSettings:
    return AppSettings.get().billing
