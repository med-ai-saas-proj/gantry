"""Environment settings for the Organization module."""

from src.settings import AppSettings

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


@AppSettings.register("org")
class OrgSetting(BaseSettings):
    keycloak_service_client_id: str = Field(
        "med-ai-saas-backend",
        validation_alias="KEYCLOAK_SERVICE_CLIENT_ID",
        description="Service account client id for Keycloak Admin API calls.",
    )
    keycloak_service_client_secret: str = Field(
        ...,
        validation_alias="KEYCLOAK_SERVICE_CLIENT_SECRET",
        description=(
            "Service account client secret for Keycloak Admin API calls."
        ),
    )
    default_rate_limit: int | None = Field(
        None,
        description=(
            "Global default rate-limit (requests/min). "
            "Individual orgs can override this."
        ),
    )
    deletion_cancel_window_days: int = Field(
        30,
        ge=1,
        description=(
            "How many days an org deletion request can be canceled "
            "before hard deletion."
        ),
    )
    deletion_worker_interval_seconds: int = Field(
        60,
        ge=5,
        description="Background worker interval for processing due deletions.",
    )


@lru_cache(1)
def getOrgSettings() -> OrgSetting:
    return OrgSetting()
