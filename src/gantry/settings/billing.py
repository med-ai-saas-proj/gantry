from typing import Annotated

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BillingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="billing_source_", case_sensitive=False
    )

    stripe_secret_key: Annotated[
        SecretStr,
        Field(description="Stripe API secret key."),
    ]
    stripe_webhook_secret: Annotated[
        SecretStr,
        Field(description="Stripe webhook signing secret."),
    ]

    invoice_process_interval_seconds: Annotated[
        int,
        Field(
            description="Interval in seconds for processing invoices in the management service",
        ),
    ] = 60

    transaction_expire_check_interval_seconds: Annotated[
        int,
        Field(
            description="Interval in seconds for checking and closing expired transactions",
        ),
    ] = 60
