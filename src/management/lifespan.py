from src.management.billing.settings import getBillingSetting
from src.management.billing.factories import (
    getInvoiceService,
    getBillingTransactionService,
)
from src.management.organization.settings import getOrgSettings
from src.management.organization.factories import getOrgService

import asyncio

from fastapi import FastAPI


org_deletion_task: asyncio.Task | None = None
billing_process_task: asyncio.Task | None = None
invoice_process_task: asyncio.Task | None = None


async def _org_delete_worker_loop():
    service = getOrgService()
    while True:
        try:  # noqa: SIM105
            await service.processDueDeletions()
        except Exception:
            # Keep loop alive; failures are logged in service/global handlers.
            pass
        await asyncio.sleep(getOrgSettings().deletion_worker_interval_seconds)


async def invoice_process_loop():
    service = getInvoiceService()
    await service.processInvoicesTask(
        getBillingSetting().invoice_process_interval_seconds
    )


async def billing_process_loop():
    trx_service = getBillingTransactionService()
    await trx_service.closeExpiredTransactionsTask(
        getBillingSetting().transaction_expire_check_interval_seconds
    )


async def startup(app: FastAPI):
    # Startup code here
    global org_deletion_task, billing_process_task, invoice_process_task
    org_deletion_task = asyncio.create_task(_org_delete_worker_loop())
    billing_process_task = asyncio.create_task(billing_process_loop())
    invoice_process_task = asyncio.create_task(invoice_process_loop())


async def shutdown(app: FastAPI):
    # Cleanup code here
    global org_deletion_task, billing_process_task, invoice_process_task
    if org_deletion_task:
        org_deletion_task.cancel()
        try:
            await org_deletion_task
        except Exception:
            pass

    if billing_process_task:
        billing_process_task.cancel()
        try:
            await billing_process_task
        except Exception:
            pass

    if invoice_process_task:
        invoice_process_task.cancel()
        try:
            await invoice_process_task
        except Exception:
            pass
