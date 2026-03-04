"""Factory functions for the Organization module singletons."""

from src.db.factories import getSessionManager
from src.shared.utils.logger import getLogger
from src.management.auth.settings import getAuthSettings

from .services import OrgService
from .settings import getOrgSettings
from .repositories import (
    OrgSettingsRepository,
    OrgDeletionRequestRepository,
)
from .keycloak_client import KeycloakOrgClient

from functools import lru_cache


@lru_cache(1)
def getKeycloakOrgClient() -> KeycloakOrgClient:
    """Singleton Keycloak Organisation client."""
    auth = getAuthSettings()
    org_settings = getOrgSettings()

    return KeycloakOrgClient(
        server_url=auth.server_url.encoded_string(),
        realm=auth.realm_name,
        service_client_id=org_settings.keycloak_service_client_id,
        service_client_secret=org_settings.keycloak_service_client_secret,
    )


@lru_cache(1)
def getOrgService() -> OrgService:
    """Singleton OrgService."""
    return OrgService(
        kc_client=getKeycloakOrgClient(),
        settings_repo=OrgSettingsRepository(),
        deletion_repo=OrgDeletionRequestRepository(),
        session_manager=getSessionManager(),
        logger=getLogger(),
    )
