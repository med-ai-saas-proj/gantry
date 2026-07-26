from gantry.management.auth.entities import UserInfo
from gantry.management.auth.dependencies import getUserInfo
from gantry.management.project.factories import getProjectService
from gantry.management.project.permissions import ProjectPermission
from gantry.management.project.dependencies import (
    assertProjectRole,
    assertProjectsRole,
)
from gantry.management.organization.permissions import OrgPermission
from gantry.management.organization.dependencies import requiredOrgPermission
from gantry.shared.custom_types.responses.response import (
    ObjectResponse,
    PaginatedResponse,
)

from ..dtos import TransactionInfoResponse
from .router import billing_router
from ..factories import getBillingTransactionService
from ..services.transaction_services import TransactionService

from uuid import UUID
from typing import Annotated
from datetime import datetime

from fastapi import Query, Security
from fastapi.params import Depends


@billing_router.get(
    "/transactions",
    description="List transactions with optional filters (e.g. project_id, date range, etc.). Supports pagination.",
)
async def listTransactions(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.BILLING_VIEW_USAGE)),
    ],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
    project_uuids: list[UUID] | None = Query(
        None
    ),  # filter by project_uuid or whole organization
    start_date: datetime | None = None,  # ISO date string
    end_date: datetime | None = None,  # ISO date string
    limit: int = 100,
    offset: int = 0,
) -> PaginatedResponse[TransactionInfoResponse]:
    project_uids_set = (
        [str(uid) for uid in project_uuids] if project_uuids else []
    )

    if project_uids_set:
        await assertProjectsRole(
            project_service=getProjectService(),
            user_info=user_info,
            project_uuids=project_uids_set,
            required_permissions=[ProjectPermission.MEMBER],
        )
        project_uuids = [UUID(uid) for uid in project_uids_set]
    else:  # if no project_uids filter provided, default to all projects user has access to
        project_uuids = [
            UUID(uid) for uid in user_info["project_permissions"].keys()
        ]

    res, total = await billing_service.getTransactions(
        org_id=user_info["org_uuid"],
        project_uuids=project_uuids,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return PaginatedResponse[TransactionInfoResponse](
        data=res, total=total, offset=offset, limit=limit
    )


@billing_router.get(
    "/transactions/{transaction_uid}",
    description="Get details for a specific transaction, including amount, date, associated project, etc.",
)
async def getTransactionDetails(
    transaction_uid: UUID,
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.BILLING_VIEW_USAGE)),
    ],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
) -> ObjectResponse[TransactionInfoResponse]:
    res = (
        await billing_service.getTransactionById(
            org_id=user_info["org_uuid"], transaction_uid=transaction_uid
        )
    ).unwrap()

    await assertProjectRole(
        project_service=getProjectService(),
        user_info=user_info,
        project_uuid=str(res.project_uuid),
        required_permissions=[ProjectPermission.MEMBER],
    )

    return ObjectResponse[TransactionInfoResponse](data=res)
