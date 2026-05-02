"""Factory functions for the Organization module singletons."""

from gantry.db import getRedis, getSessionManager
from gantry.keycloak import (
    KeycloakServiceClient,
    getKeycloakServiceClient,
)
from gantry.shared.logging.logger import getLogger

from .services import OrgService
from .settings import getOrgSettings
from .repositories import (
    OrgSettingsRepository,
    OrgDeletionRequestRepository,
)

from functools import lru_cache


@lru_cache(1)
def getKeycloakOrgServiceClient() -> KeycloakServiceClient:
    """Singleton Keycloak Organisation client."""
    org_settings = getOrgSettings()

    return getKeycloakServiceClient(
        org_settings.keycloak_service_client_id,
        org_settings.keycloak_service_client_secret,
    )


@lru_cache(1)
def getOrgService() -> OrgService:
    """Singleton OrgService."""
    return OrgService(
        kc_client=getKeycloakOrgServiceClient(),
        settings_repo=OrgSettingsRepository(),
        deletion_repo=OrgDeletionRequestRepository(),
        session_manager=getSessionManager(),
        logger=getLogger(),
        redis=getRedis(),
    )
