from gantry.management.auth.entities import UserInfo
from gantry.management.auth.dependencies import getUserInfo

from ..factories import getInvoiceService
from .internal_router import internal_billing_router
from ..services.invoice_service import InvoiceService

from uuid import UUID
from typing import Annotated

from fastapi import Depends


@internal_billing_router.put(
    "/invoices/{invoice_uid}/mark_paid",
    tags=["admin"],
    description="Manually mark an invoice as paid. This is useful for offline payments or when payment confirmation is received outside of the normal payment flow.",
)
async def mark_invoice_as_paid(
    invoice_uid: UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    invoice_service: Annotated[InvoiceService, Depends(getInvoiceService)],
):
    (
        await invoice_service.markInvoiceAsPaidManually(
            org_id=user_info["org_uuid"], invoice_uid=invoice_uid
        )
    ).unwrap()


@internal_billing_router.post(
    "/invoices/{invoice_uid}/refund",
    tags=["admin"],
    description="Manually mark an invoice as refunded. This is useful for issuing refunds outside of the normal flow, such as when a refund is processed directly through the payment gateway or for offline refunds.",
)
async def mark_invoice_as_refunded(
    invoice_uid: UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    invoice_service: Annotated[InvoiceService, Depends(getInvoiceService)],
):
    (
        await invoice_service.markInvoiceAsRefundedManually(
            org_id=user_info["org_uuid"], invoice_uid=invoice_uid
        )
    ).unwrap()
