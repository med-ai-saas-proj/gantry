from src.management.billing.settings import BillingSetting, getBillingSetting

from .router import billing_router

from typing import Annotated, cast
from datetime import UTC, datetime

import stripe
from fastapi import Depends, Request, HTTPException
from src.management.billing.models import BillingSourceProvider
from src.management.billing.factories import getInvoiceService
from src.management.billing.services.invoice_service import InvoiceService


@billing_router.post(
    "/webhook/stripe",
    tags=["webhook"],
    description="Endpoint to receive Stripe webhooks for billing events (e.g. invoice paid). This endpoint is used by Stripe and mustn't be called directly by clients.",
)
async def stripe_webhook(
    request: Request,
    billing_setting: Annotated[BillingSetting, Depends(getBillingSetting)],
    invoice_service: Annotated[InvoiceService, Depends(getInvoiceService)],
) -> dict:
    webhook_secret = billing_setting.stripe_webhook_secret

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Verify signature
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(
            status_code=400, detail={"message": "Invalid signature"}
        )
    except Exception:
        raise HTTPException(
            status_code=400, detail={"message": "Invalid payload"}
        )

    # Handle event types
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "invoice.paid":
        data = cast(stripe.Invoice, data)
        paid_at = data.status_transitions.paid_at
        if (
            not paid_at or data.status != "paid"
        ):  # should never happen since we are in invoice.paid event, but just to be safe
            raise HTTPException(
                status_code=400,
                detail={"message": "Invoice not marked as paid"},
            )
        res = await invoice_service.markInvoiceAsPaid(
            BillingSourceProvider.STRIPE,
            data.id,
            datetime.fromtimestamp(paid_at)
            .astimezone(UTC)
            .replace(tzinfo=None),
        )
        res.unwrap()

    return {"received": True}
