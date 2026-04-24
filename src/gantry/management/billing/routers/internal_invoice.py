from gantry.management.billing.dtos import (
    InvoiceInfoResponse,
    InvoiceDetailInfoResponse,
)
from gantry.management.auth.entities import UserInfo
from gantry.management.auth.dependencies import getUserInfo
from gantry.shared.custom_types.responses.response import (
    ObjectResponse,
    PaginatedResponse,
)

from ..factories import getInvoiceService
from .internal_router import internal_billing_router
from ..services.invoice_service import InvoiceService

from uuid import UUID
from typing import Annotated
from datetime import datetime

from fastapi import Depends


@internal_billing_router.put(
    "/invoices/{invoice_uid}/mark_paid",
    tags=["admin"],
    description="Manually mark an invoice as paid. This is useful for offline payments or when payment confirmation is received outside of the normal payment flow.",
)
async def mark_invoice_as_paid(
    invoice_uid: UUID,
    # TODO: use admin dependency here
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    invoice_service: Annotated[InvoiceService, Depends(getInvoiceService)],
):
    (
        await invoice_service.markInvoiceAsPaidManually(invoice_uid=invoice_uid)
    ).unwrap()


@internal_billing_router.post(
    "/invoices/{invoice_uid}/refund",
    tags=["admin"],
    description="Manually mark an invoice as refunded. This is useful for issuing refunds outside of the normal flow, such as when a refund is processed directly through the payment gateway or for offline refunds.",
)
async def mark_invoice_as_refunded(
    invoice_uid: UUID,
    # TODO: use admin dependency here
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    invoice_service: Annotated[InvoiceService, Depends(getInvoiceService)],
):
    (
        await invoice_service.markInvoiceAsRefundedManually(
            invoice_uid=invoice_uid
        )
    ).unwrap()


@internal_billing_router.get(
    "/invoices",
    description="List invoices, with filters for project_id, billing_period, payment_status, etc.",
)
async def list_invoices(
    # TODO: use admin dependency here
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    invoice_service: Annotated[InvoiceService, Depends(getInvoiceService)],
    org_ids: list[str] | None = None,
    from_date: datetime | None = None,  # ISO date string
    to_date: datetime | None = None,  # ISO date string
    paid: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> PaginatedResponse[InvoiceInfoResponse]:
    invoices, total = (
        await invoice_service.listInvoicesForAdmin(
            org_ids=org_ids,
            offset=offset,
            limit=limit,
            from_date=from_date,
            to_date=to_date,
            paid=paid,
        )
    ).unwrap()
    return PaginatedResponse(
        data=invoices,
        total=total,
        limit=limit,
        offset=offset,
    )


@internal_billing_router.get(
    "/invoices/{invoice_uid}",
    description="Get invoice details, including line items and payment status.",
)
async def get_invoice_details(
    invoice_uid: UUID,
    # TODO: use admin dependency here
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    invoice_service: Annotated[InvoiceService, Depends(getInvoiceService)],
) -> ObjectResponse[InvoiceDetailInfoResponse]:
    res = (
        await invoice_service.getInvoiceByIdForAdmin(invoice_uid=invoice_uid)
    ).unwrap()
    return ObjectResponse(data=res)
