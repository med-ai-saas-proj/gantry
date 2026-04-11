from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BillingSetting(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="billing_source_", case_sensitive=False
    )

    stripe_secret_key: SecretStr
    stripe_webhook_secret: SecretStr

    invoice_process_interval_seconds: int = Field(
        600,
        description="Interval in seconds for processing invoices in the management service",
    )

    transaction_expire_check_interval_seconds: int = Field(
        600,
        description="Interval in seconds for checking and closing expired transactions",
    )


@lru_cache(1)
def getBillingSetting() -> BillingSetting:
    return BillingSetting()  # type: ignore
