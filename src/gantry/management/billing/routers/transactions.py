from gantry.management.auth.roles import ManagementRole
from gantry.management.auth.entities import UserInfo
from gantry.management.auth.dependencies import getUserInfo, requireRole
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

from fastapi import Query, Depends


@billing_router.get(
    "/transactions",
    description="List transactions with optional filters (e.g. project_id, date range, etc.). Supports pagination.",
)
async def listTransactions(
    user_info: Annotated[
        UserInfo, Depends(requireRole(ManagementRole.BILLING_VIEW_USAGE))
    ],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
    project_uids: list[UUID] | None = Query(
        None
    ),  # filter by project_uid or whole organization
    start_date: datetime | None = None,  # ISO date string
    end_date: datetime | None = None,  # ISO date string
    limit: int = 100,
    offset: int = 0,
) -> PaginatedResponse[TransactionInfoResponse]:
    res, total = await billing_service.getTransactions(
        org_id=user_info["org_id"],
        project_uids=project_uids,
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
        UserInfo, Depends(requireRole(ManagementRole.BILLING_VIEW_USAGE))
    ],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
) -> ObjectResponse[TransactionInfoResponse]:
    res = (
        await billing_service.getTransactionById(
            org_id=user_info["org_id"], transaction_uid=transaction_uid
        )
    ).unwrap()
    return ObjectResponse[TransactionInfoResponse](data=res)
