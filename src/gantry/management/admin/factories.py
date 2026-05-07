"""Factory functions for Admin module singletons."""

from gantry.db import getSessionManager
from gantry.management.api_key.factories import (
    getApiKeyService,
    getApiKeyRepository,
)
from gantry.management.project.factories import (
    getProjectService,
    getProjectRepository,
)
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
        project_repo=getProjectRepository(),
        api_key_repo=getApiKeyRepository(),
    )
