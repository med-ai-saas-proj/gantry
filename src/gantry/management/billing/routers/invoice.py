from gantry.management.auth.entities import UserInfo
from gantry.management.auth.dependencies import getUserInfo
from gantry.shared.custom_types.responses.response import (
    ObjectResponse,
    PaginatedResponse,
)

from ..dtos import (
    InvoiceInfoResponse,
    ManualPaymentResponse,
    InvoiceDetailInfoResponse,
)
from .router import billing_router
from ..factories import getInvoiceService
from ..services.invoice_service import InvoiceService

from uuid import UUID
from typing import Annotated
from datetime import datetime

from fastapi import Depends


@billing_router.get(
    "/invoices",
    description="List invoices, with filters for project_id, billing_period, payment_status, etc.",
)
async def list_invoices(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    invoice_service: Annotated[InvoiceService, Depends(getInvoiceService)],
    from_date: datetime | None = None,  # ISO date string
    to_date: datetime | None = None,  # ISO date string
    paid: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> PaginatedResponse[InvoiceInfoResponse]:
    invoices, total = (
        await invoice_service.listInvoices(
            org_id=user_info["org_id"],
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


@billing_router.get(
    "/invoices/{invoice_uid}",
    description="Get invoice details, including line items and payment status.",
)
async def get_invoice_details(
    invoice_uid: UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    invoice_service: Annotated[InvoiceService, Depends(getInvoiceService)],
) -> ObjectResponse[InvoiceDetailInfoResponse]:
    res = (
        await invoice_service.getInvoiceById(
            org_id=user_info["org_id"], invoice_uid=invoice_uid
        )
    ).unwrap()
    return ObjectResponse(data=res)


@billing_router.post(
    "/invoices/{invoice_uid}/pay",
    description="Manually trigger payment for an invoice. Useful for retrying failed payments. Returning a payment gateway hosted payment URL",
)
async def pay_invoice(
    invoice_uid: UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    invoice_service: Annotated[InvoiceService, Depends(getInvoiceService)],
) -> ObjectResponse[ManualPaymentResponse]:
    res = await invoice_service.getInvoiceByIdPaymentLinkInProvider(
        org_id=user_info["org_id"], invoice_uid=invoice_uid
    )
    return ObjectResponse(
        data=ManualPaymentResponse(hosted_invoice_url=res.unwrap())
    )


@billing_router.put(
    "/invoices/{invoice_uid}/mark_paid",
    tags=["admin"],
    description="Manually mark an invoice as paid. This is useful for offline payments or when payment confirmation is received outside of the normal payment flow.",
)
async def mark_invoice_as_paid(
    invoice_uid: UUID,
    user_info: Annotated[
        UserInfo, Depends(getUserInfo)
    ],  # TODO: use admin auth dependency
    invoice_service: Annotated[InvoiceService, Depends(getInvoiceService)],
):
    (
        await invoice_service.markInvoiceAsPaidManually(
            org_id=user_info["org_id"], invoice_uid=invoice_uid
        )
    ).unwrap()


@billing_router.post(
    "/invoices/{invoice_uid}/refund",
    tags=["admin"],
    description="Manually mark an invoice as refunded. This is useful for issuing refunds outside of the normal flow, such as when a refund is processed directly through the payment gateway or for offline refunds.",
)
async def mark_invoice_as_refunded(
    invoice_uid: UUID,
    user_info: Annotated[
        UserInfo, Depends(getUserInfo)
    ],  # TODO: use admin auth dependency
    invoice_service: Annotated[InvoiceService, Depends(getInvoiceService)],
):
    (
        await invoice_service.markInvoiceAsRefundedManually(
            org_id=user_info["org_id"], invoice_uid=invoice_uid
        )
    ).unwrap()
