from src.management.billing.dtos import (
    InvoiceInfoResponse,
    ManualPaymentResponse,
)
from src.management.auth.entities import UserInfo
from src.management.auth.dependencies import getUserInfo
from src.shared.custom_types.responses.response import (
    ObjectResponse,
    PaginatedResponse,
)

from .router import billing_router
from ..factories import getBillingTransactionService
from ..services.transaction_services import TransactionService

import enum
from uuid import UUID
from typing import Annotated
from datetime import datetime

from regex import P
from fastapi import Depends


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


@billing_router.get(
    "/invoices",
    description="List invoices, with filters for project_id, billing_period, payment_status, etc.",
)
async def list_invoices(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
    project_uid: list[UUID]
    | None = None,  # filter by project_uid or whole organization
    from_date: datetime | None = None,  # ISO date string
    to_date: datetime | None = None,  # ISO date string
    payment_status: list[PaymentStatus]
    | None = None,  # e.g. "paid", "unpaid", "overdue"
    limit: int = 100,
    offset: int = 0,
) -> PaginatedResponse[InvoiceInfoResponse]:
    pass


@billing_router.get(
    "/invoices/{invoice_uid}",
    description="Get invoice details, including line items and payment status.",
)
async def get_invoice_details(
    invoice_uid: UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
) -> ObjectResponse[InvoiceInfoResponse]:
    pass


@billing_router.post(
    "/invoices/{invoice_uid}/pay",
    description="Manually trigger payment for an invoice. Useful for retrying failed payments. Returning a payment gateway hosted payment URL",
)
async def pay_invoice(
    invoice_uid: UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
) -> ObjectResponse[ManualPaymentResponse]:
    return ObjectResponse(
        data=ManualPaymentResponse(
            hosted_invoice_url="https://example.com/payment"
        )
    )
