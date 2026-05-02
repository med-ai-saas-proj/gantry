"""Factory functions for the Organization module singletons."""

from gantry.db import getRedis, getSessionManager
from gantry.keycloak import (
    KeycloakServiceClient,
    getKeycloakServiceClient as getBaseKeycloakServiceClient,
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

    return getBaseKeycloakServiceClient(
        org_settings.keycloak_service_client_id,
        org_settings.keycloak_service_client_secret,
    )


@lru_cache(1)
def getKeycloakServiceClient() -> KeycloakServiceClient:
    """Compatibility dependency for modules that need the org service client."""
    return getKeycloakOrgServiceClient()


@lru_cache(1)
def getOrgService() -> OrgService:
    """Singleton OrgService."""
    return OrgService(
        kc_client=getKeycloakServiceClient(),
        settings_repo=OrgSettingsRepository(),
        deletion_repo=OrgDeletionRequestRepository(),
        session_manager=getSessionManager(),
        logger=getLogger(),
        redis=getRedis(),
    )
