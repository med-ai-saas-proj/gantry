"""Factory functions for Project module singletons."""

from src.db.factories import getRedis, getSessionManager
from src.shared.logging.logger import getLogger
from src.management.organization.factories import getKeycloakOrgClient

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
