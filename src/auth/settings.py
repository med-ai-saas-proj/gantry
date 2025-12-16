from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSetting(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="auth_", case_sensitive=False)
    access_token_secret: SecretStr
    access_token_expire_minutes: int = Field(gt=0, default=30)
    refresh_token_secret: SecretStr
    refresh_token_expire_days: int = Field(gt=1, default=15)
    api_key_secret: SecretStr
    api_key_secret_length: int = Field(gt=16, default=32)
    api_key_expire_days: int = Field(gt=1)
    max_login_attempts: int = Field(gt=0, default=5)
    login_attempt_window_minutes: int = Field(gt=0, default=15)

    keycloak_enabled: bool = Field(default=True)
    keycloak_server_url: str = Field(..., description="http://localhost:8080")
    keycloak_realm: str = Field(..., description="venera")
    keycloak_client_id: str = Field(..., description="venera-frontend")


@lru_cache(1)
def getAuthSettings() -> AuthSetting:
    return AuthSetting()
