"""Environment settings for the Organization module."""

from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings


class OrgSettings(BaseSettings):
    invite_client_id: Annotated[
        str,
        Field(
            description=(
                "Keycloak public client id used for invitation registration "
                "links and post-accept redirects."
            ),
        ),
    ] = "gantry-frontend"

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
