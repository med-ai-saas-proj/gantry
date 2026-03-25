from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BillingSourceSetting(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="billing_source_", case_sensitive=False
    )

    stripe_secret_key: SecretStr = Field()


def getBillingSourceSetting() -> BillingSourceSetting:
    return BillingSourceSetting()
