from gantry.management.auth.entities import AdminInfo
from gantry.management.auth.dependencies import getAdminInfo
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

from fastapi import Query
from fastapi.params import Depends


@billing_router.get(
    "/admin/transactions",
    description="List transactions with optional filters (e.g. project_id, date range, etc.). Supports pagination.",
    tags=["admin"],
)
async def listTransactions(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
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
    res, total = await billing_service.getTransactionsForAdmin(
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
    "/admin/transactions/{transaction_uid}",
    description="Get details for a specific transaction, including amount, date, associated project, etc.",
    tags=["admin"],
)
async def getTransactionDetails(
    transaction_uid: UUID,
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
) -> ObjectResponse[TransactionInfoResponse]:
    res = (
        await billing_service.getTransactionByIdForAdmin(
            transaction_uid=transaction_uid
        )
    ).unwrap()

    return ObjectResponse[TransactionInfoResponse](data=res)
