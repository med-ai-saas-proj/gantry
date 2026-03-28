from src.management.billing.dtos import (
    InvoiceInfoResponse,
    ManualPaymentResponse,
    TransactionInfoResponse,
)
from src.management.auth.entities import UserInfo
from src.management.auth.dependencies import getUserInfo

from .router import billing_router
from ..factories import getBillingTransactionService
from ..services.transaction_services import BillingTransactionService

import enum
from uuid import UUID
from typing import Annotated
from datetime import datetime

from fastapi import Depends
from pydantic import BaseModel


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
        BillingTransactionService, Depends(getBillingTransactionService)
    ],
    project_uid: list[UUID]
    | None = None,  # filter by project_uid or whole organization
    from_date: datetime | None = None,  # ISO date string
    to_date: datetime | None = None,  # ISO date string
    payment_status: list[PaymentStatus]
    | None = None,  # e.g. "paid", "unpaid", "overdue"
    limit: int = 100,
    offset: int = 0,
) -> list[InvoiceInfoResponse]:
    pass


@billing_router.get(
    "/invoices/{invoice_uid}",
    description="Get invoice details, including line items and payment status.",
)
async def get_invoice_details(
    invoice_uid: UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[
        BillingTransactionService, Depends(getBillingTransactionService)
    ],
) -> InvoiceInfoResponse:
    pass


@billing_router.post(
    "/invoices/{invoice_uid}/pay",
    description="Manually trigger payment for an invoice. Useful for retrying failed payments. Returning a payment gateway hosted payment URL",
)
async def pay_invoice(
    invoice_uid: UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[
        BillingTransactionService, Depends(getBillingTransactionService)
    ],
) -> ManualPaymentResponse:
    return ManualPaymentResponse(
        hosted_invoice_url="https://example.com/payment"
    )
