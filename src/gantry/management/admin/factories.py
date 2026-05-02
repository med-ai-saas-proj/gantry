"""Factory functions for Admin module singletons."""

from gantry.db import getSessionManager
from gantry.management.api_key.factories import getApiKeyService
from gantry.management.project.factories import getProjectService
from gantry.management.api_key.repositories import ApiKeyRepository
from gantry.management.project.repositories import ProjectRepository
from gantry.management.organization.factories import (
    getOrgService,
    getKeycloakServiceClient,
)

from .services import AdminService

from functools import lru_cache


@lru_cache(1)
def getAdminService() -> AdminService:
    """Singleton AdminService."""
    return AdminService(
        session_manager=getSessionManager(),
        kc_org_client=getKeycloakServiceClient(),
        org_service=getOrgService(),
        project_service=getProjectService(),
        apikey_service=getApiKeyService(),
        project_repo=ProjectRepository(),
        api_key_repo=ApiKeyRepository(),
    )
