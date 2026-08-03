from gantry.db.factories import getRedisCacheRepo, getSessionManager
from gantry.management.project.repositories import ProjectRepository

import uuid
from typing import Annotated

from fastapi import Query, Header, HTTPException


async def getOptionalProjectId(
    x_project_uuid: Annotated[
        uuid.UUID | None, Header(alias="X-Project-UUID")
    ] = None,
    project_uuid: Annotated[
        uuid.UUID | None, Query(alias="project_uuid")
    ] = None,
) -> int | None:
    if x_project_uuid is not None and project_uuid is not None:
        raise HTTPException(
            status_code=400,
            detail="project_uuid must be provided via X-Project-UUID header or project_uuid query param, not both",
        )
    resolved = x_project_uuid or project_uuid
    if resolved is None:
        return None
    repo = ProjectRepository(getRedisCacheRepo())
    async with getSessionManager().get_session() as session:
        project = await repo.getByUuid(session, str(resolved))
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project.id


async def getProjectId(
    x_project_uuid: Annotated[
        uuid.UUID | None, Header(alias="X-Project-UUID")
    ] = None,
    project_uuid: Annotated[
        uuid.UUID | None, Query(alias="project_uuid")
    ] = None,
) -> int:
    if x_project_uuid is not None and project_uuid is not None:
        raise HTTPException(
            status_code=400,
            detail="project_uuid must be provided via X-Project-UUID header or project_uuid query param, not both",
        )
    resolved = x_project_uuid or project_uuid
    if resolved is None:
        raise HTTPException(
            status_code=400,
            detail="project_uuid is required (via X-Project-UUID header or project_uuid query param)",
        )
    repo = ProjectRepository(getRedisCacheRepo())
    async with getSessionManager().get_session() as session:
        project = await repo.getByUuid(session, str(resolved))
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project.id


async def resolveProjectId(project_uuid: uuid.UUID) -> int:
    repo = ProjectRepository(getRedisCacheRepo())
    async with getSessionManager().get_session() as session:
        project = await repo.getByUuid(session, str(project_uuid))
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project.id
