"""Environment settings for the Organization module."""

from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings


class OrgSettings(BaseSettings):
    keycloak_service_client_id: Annotated[
        str,
        Field(
            description="Service account client id for Keycloak Admin API calls.",
        ),
    ] = "med-ai-saas-backend"

    keycloak_service_client_secret: Annotated[
        str,
        Field(
            description="Service account client secret for Keycloak Admin API calls.",
        ),
    ]

    invite_client_id: Annotated[
        str,
        Field(
            description="OIDC client id used for invitation registration links.",
        ),
    ]

    invite_redirect_uri: Annotated[
        str,
        Field(
            description="Redirect URI used for invitation registration links.",
        ),
    ] = "http://localhost:3000"

    default_rate_limit: Annotated[
        int | None,
        Field(
            description="Global default rate-limit (requests/min). Individual orgs can override this.",
        ),
    ] = None

    deletion_cancel_window_days: Annotated[
        int,
        Field(
            ge=1,
            description="How many days an org deletion request can be canceled before hard deletion.",
        ),
    ] = 30

    deletion_worker_interval_seconds: Annotated[
        int,
        Field(
            ge=5,
            description="Background worker interval for processing due deletions.",
        ),
    ] = 60
