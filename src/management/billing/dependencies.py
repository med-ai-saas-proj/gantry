from src.db.factories import getSessionManager
from src.management.projects.models import Project
from src.management.api_keys.entities import ApiKeyInfo
from src.management.api_keys.dependencies import requiredPermissions
from src.shared.custom_types.error_exception import RecoverableError

from typing import Annotated, TypedDict

from fastapi import Depends
from sqlalchemy import select


class BillingContext(TypedDict):
    """Fully resolved caller identity for a billing request."""

    apikey_id: int  # integer PK of the verified ApiKey row
    project_id: int  # project the key belongs to
    organization_id: str  # org the project belongs to
    org_project_ids: list[
        int
    ]  # all project IDs in the same org (for org-total cap)


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class BillingContextResolutionError(RecoverableError):
    status = 403
    code = "billing_context_error"
    title = "Billing Context Error"
    detail = "Could not resolve organization context for the provided API key."


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------


async def get_billing_context(
    # Reuse existing API key verification — passes permission check too.
    # billing:write is the permission required to trigger charges.
    key_info: Annotated[
        ApiKeyInfo, Depends(requiredPermissions(["billing:write"]))
    ],
) -> BillingContext:
    """Resolve full billing context from the verified API key.

    This verifies the key→project ownership implicitly (if project_id from
    the verified key doesn't exist in Project table, query returns nothing
    and we raise 403 — no way to forge a project_id that way).
    """
    project_id: int = key_info["project_id"]

    # Collect all sibling project IDs including this project's own ID
    stmt = (
        select(
            Project.organization_id,
        )
        .where(Project.id == project_id)
        .limit(1)
    )

    session_manager = getSessionManager()
    async with session_manager.get_session() as session:
        # Get org_id for this project
        result = await session.execute(stmt)
        row = result.first()

        if row is None:
            # project_id from ApiKey points to a non-existent project — data
            # integrity issue, but we surface it as a 403 to the caller.
            raise BillingContextResolutionError()

        org_id: str = row.organization_id

        # Get all project IDs in the same org (single IN-free query)
        sibling_stmt = select(Project.id).where(
            Project.organization_id == org_id
        )
        sibling_result = await session.execute(sibling_stmt)
        org_project_ids: list[int] = [r[0] for r in sibling_result.all()]

    return BillingContext(
        apikey_id=key_info["api_key_id"],
        project_id=project_id,
        organization_id=org_id,
        org_project_ids=org_project_ids,
    )
