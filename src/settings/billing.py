from pydantic import SecretStr
from pydantic_settings import BaseSettings


class BillingSourceSettings(BaseSettings):
    stripe_secret_key: SecretStr
