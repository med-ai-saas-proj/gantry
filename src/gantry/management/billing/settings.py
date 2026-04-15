from gantry.settings import AppSettings, BillingSettings


def getBillingSetting() -> BillingSettings:
    return AppSettings.get().billing
