"""Factory functions for the Organization module singletons."""

from src.db.factories import getSessionManager
from src.shared.utils.logger import getLogger
from src.management.auth.settings import getAuthSettings

from .services import OrgService
from .repositories import (
    OrgProjectRepository,
    OrgMetadataRepository,
    OrgSettingsRepository,
    OrgInvitationRepository,
    OrgDeletionRequestRepository,
)
from .keycloak_client import KeycloakOrgClient

import os
from functools import lru_cache


@lru_cache(1)
def getKeycloakOrgClient() -> KeycloakOrgClient:
    """Singleton Keycloak Organisation client."""
    auth = getAuthSettings()
    service_client_secret = os.getenv("KEYCLOAK_SERVICE_CLIENT_SECRET", "")
    if not service_client_secret:
        raise ValueError(
            "KEYCLOAK_SERVICE_CLIENT_SECRET must be set for organization "
            "Keycloak client."
        )

    return KeycloakOrgClient(
        server_url=auth.server_url.encoded_string(),
        realm=auth.realm_name,
        service_client_id=os.getenv(
            "KEYCLOAK_SERVICE_CLIENT_ID",
            "med-ai-saas-backend",
        ),
        service_client_secret=service_client_secret,
    )


@lru_cache(1)
def getOrgService() -> OrgService:
    """Singleton OrgService."""
    return OrgService(
        kc_client=getKeycloakOrgClient(),
        settings_repo=OrgSettingsRepository(),
        metadata_repo=OrgMetadataRepository(),
        deletion_repo=OrgDeletionRequestRepository(),
        project_repo=OrgProjectRepository(),
        invitation_repo=OrgInvitationRepository(),
        session_manager=getSessionManager(),
        logger=getLogger(),
    )
