from __future__ import annotations

from decimal import Decimal

import pytest
from freezegun import freeze_time
from pyrusult import ResultStatus

pytestmark = pytest.mark.integration


async def _create_billing_subject(org_id: str):
    from gantry.db.factories import getSessionManager
    from gantry.management.api_key.factories import getApiKeyService
    from gantry.management.organization.factories import getOrgSettingsRepository
    from gantry.management.project.factories import (
        getProjectRepository,
        getProjectSettingsRepository,
    )

    session_manager = getSessionManager()
    project_repo = getProjectRepository()
    org_settings_repo = getOrgSettingsRepository()
    project_settings_repo = getProjectSettingsRepository()
    async with session_manager.get_session() as session:
        await org_settings_repo.upsert(
            session,
            org_id=org_id,
            rate_limit=240,
            spending_limit=100,
            extra={"billing": "integration"},
        )
        project = await project_repo.create(
            session,
            name="Integration Billing Project",
            description="Project for billing integration tests",
            organization_id=org_id,
        )
        await project_settings_repo.upsert(
            session,
            project_id=project.id,
            rate_limit=120,
            spending_limit=20,
            extra={"billing": "project"},
        )
        await session.commit()
        project_id = project.id
        project_uuid = str(project.uuid)

    api_key_service = getApiKeyService()
    created_key = (
        await api_key_service.createApiKey(
            actor_user_id="gantry-test-user",
            project_uuid=project_uuid,
            name="billing key",
            description="billing story key",
            permissions=["chat.run"],
        )
    ).unwrap()
    internal_ids = (
        await api_key_service.getApiKeyInternalIds(created_key.api_key_uuid)
    ).unwrap()
    return project_id, project_uuid, created_key.api_key_uuid


@pytest.mark.asyncio
async def test_billing_spending_limits_load_from_db_then_cache_and_invalidate(
    migrated_management_storage,
    integration_stack,
) -> None:
    from gantry.db.factories import getRedis, getSessionManager
    from gantry.management.billing.cache_settings import (
        billing_org_spending_limit_key,
        billing_project_spending_limit_key,
    )
    from gantry.management.billing.factories import getBillingTransactionService
    from gantry.management.organization.factories import getOrgSettingsRepository
    from gantry.management.project.factories import getProjectSettingsRepository

    assert integration_stack.timescale_asyncpg_uri
    assert integration_stack.redis_url
    org_id = "integration-billing-limit-org"
    project_id, _, _ = await _create_billing_subject(org_id)
    service = getBillingTransactionService()

    first_res = await service.getSpendingLimits(org_id, project_id)
    assert first_res.status == ResultStatus.Ok
    first_project_limit, first_org_limit = first_res.unwrap()
    assert first_org_limit == Decimal("100")
    assert first_project_limit == Decimal("20")

    async with getSessionManager().get_session() as session:
        await getOrgSettingsRepository().upsert(
            session,
            org_id=org_id,
            rate_limit=240,
            spending_limit=200,
            extra={"billing": "updated"},
        )
        await getProjectSettingsRepository().upsert(
            session,
            project_id=project_id,
            rate_limit=120,
            spending_limit=40,
            extra={"billing": "updated"},
        )
        await session.commit()

    cached_res = await service.getSpendingLimits(org_id, project_id)
    assert cached_res.unwrap() == (Decimal("20"), Decimal("100"))

    redis = getRedis()
    await redis.delete(
        billing_org_spending_limit_key(org_id),
        billing_project_spending_limit_key(org_id, project_id),
    )
    reloaded_res = await service.getSpendingLimits(org_id, project_id)
    await redis.aclose()

    assert reloaded_res.status == ResultStatus.Ok
    assert reloaded_res.unwrap() == (Decimal("40"), Decimal("200"))


@pytest.mark.asyncio
async def test_billing_transaction_post_capture_and_read_path_uses_real_db_and_redis(
    migrated_management_storage,
    integration_stack,
) -> None:
    from gantry.management.billing.dtos import PostRequest
    from gantry.management.billing.factories import getBillingTransactionService
    from gantry.management.billing.models import TransactionStatus

    assert integration_stack.timescale_asyncpg_uri
    assert integration_stack.redis_url
    org_id = "integration-billing-transaction-org"
    project_id, project_uuid, api_key_uuid = await _create_billing_subject(org_id)
    service = getBillingTransactionService()

    with freeze_time("2026-05-12T10:00:00Z"):
        post_res = await service.post(
            idempotency_key="integration-billing-post",
            req=PostRequest(
                api_key_uuid=api_key_uuid,
                amount={"value": 150, "scale": 2},
                details={"model": "integration-test"},
                capture=False,
            ),
        )

    assert post_res.status == ResultStatus.Ok
    transaction_uuid = post_res.unwrap()

    capture_res = await service.capture(
        transaction_uid=transaction_uuid,
        real_amount={"value": 125, "scale": 2},
    )
    assert capture_res.status == ResultStatus.Ok

    transaction_res = await service.getTransactionById(org_id, transaction_uuid)
    transactions, total = await service.getTransactions(org_id, limit=10, offset=0)

    assert transaction_res.status == ResultStatus.Ok
    transaction = transaction_res.unwrap()
    assert str(transaction.transaction_uid) == str(transaction_uuid)
    assert str(transaction.project_uuid) == project_uuid
    assert transaction.amount == Decimal("1.25")
    assert transaction.status == TransactionStatus.CAPTURED
    assert total >= 1
    assert any(str(item.transaction_uid) == str(transaction_uuid) for item in transactions)
