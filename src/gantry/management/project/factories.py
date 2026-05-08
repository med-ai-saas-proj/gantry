"""Factory functions for Project module singletons."""

from gantry.db import getRedisCacheRepo
from gantry.keycloak import getKeycloakServiceClient
from gantry.db.factories import getRedis, getSessionManager
from gantry.shared.logging.logger import getLogger

from .services import ProjectService
from .repositories import (
    ProjectRepository,
    ProjectMemberRepository,
    ProjectSettingsRepository,
)

from functools import lru_cache


@lru_cache(1)
def getProjectRepository():
    return ProjectRepository(getRedisCacheRepo())


@lru_cache(1)
def getProjectMemeberRepository():
    return ProjectMemberRepository(getRedisCacheRepo())


@lru_cache(1)
def getProjectSettingsRepository():
    return ProjectSettingsRepository(getRedisCacheRepo())


@lru_cache(1)
def getProjectService() -> ProjectService:
    """Singleton ProjectService."""
    return ProjectService(
        session_manager=getSessionManager(),
        logger=getLogger(),
        kc_client=getKeycloakServiceClient(),
        project_repo=getProjectRepository(),
        membership_repo=getProjectMemeberRepository(),
        settings_repo=getProjectSettingsRepository(),
        redis=getRedis(),
    )
