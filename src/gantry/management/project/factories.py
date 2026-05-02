"""Factory functions for Project module singletons."""

from gantry.db.factories import getRedis, getSessionManager
from gantry.shared.logging.logger import getLogger
from gantry.management.organization.factories import (
    getKeycloakServiceClient as getKeycloakOrgClient,
)

from .services import ProjectService
from .repositories import (
    ProjectRepository,
    ProjectMemberRepository,
    ProjectSettingsRepository,
)

from functools import lru_cache


@lru_cache(1)
def getProjectService() -> ProjectService:
    """Singleton ProjectService."""
    return ProjectService(
        session_manager=getSessionManager(),
        logger=getLogger(),
        project_repo=ProjectRepository(),
        membership_repo=ProjectMemberRepository(),
        settings_repo=ProjectSettingsRepository(),
        kc_client=getKeycloakOrgClient(),
        redis=getRedis(),
    )
