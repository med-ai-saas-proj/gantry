"""Environment settings for the Organization module."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OrgSetting(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="org_", case_sensitive=False)

    default_rate_limit: int | None = Field(
        None,
        description=(
            "Global default rate-limit (requests/min). "
            "Individual orgs can override this."
        ),
    )


@lru_cache(1)
def getOrgSettings() -> OrgSetting:
    return OrgSetting()
