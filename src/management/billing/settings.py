from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BillingSourceSetting(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="billing_source_", case_sensitive=False
    )

    stripe_secret_key: SecretStr


@lru_cache(1)
def getBillingSourceSetting() -> BillingSourceSetting:
    return BillingSourceSetting()  # type: ignore
