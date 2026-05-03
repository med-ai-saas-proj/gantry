"""Factory functions for the Organization module singletons."""

from gantry.db import getSessionManager
from gantry.keycloak import getKeycloakServiceClient
from gantry.db.factories import getRedisCacheRepo
from gantry.shared.logging.logger import getLogger

from .services import OrgService
from .repositories import (
    OrgSettingsRepository,
    OrgDeletionRequestRepository,
)

from functools import lru_cache


@lru_cache(1)
def getOrgSettingsRepository():
    return OrgSettingsRepository(getRedisCacheRepo())


def getOrgDeletionRequestRepository():
    return OrgDeletionRequestRepository()


@lru_cache(1)
def getOrgService() -> OrgService:
    """Singleton OrgService."""
    return OrgService(
        kc_client=getKeycloakServiceClient(),
        settings_repo=getOrgSettingsRepository(),
        deletion_repo=getOrgDeletionRequestRepository(),
        session_manager=getSessionManager(),
        logger=getLogger(),
    )
