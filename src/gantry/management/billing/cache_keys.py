"""Shared Redis cache keys and TTLs for billing flows."""

BILLING_TRANSACTION_KEY = "billing:trx:{uuid}"
BILLING_PROJECT_SPENDING_LIMIT_KEY = (
    "billing:spending_limit:{org_id}:proj:{project_id}"
)
BILLING_ORG_SPENDING_LIMIT_KEY = "billing:spending_limit:{org_id}"
BILLING_ORG_USAGE_KEY = "billing:usage:{org_id}:{period}"
BILLING_PROJECT_USAGE_KEY = "billing:usage:{org_id}:proj:{project_id}:{period}"
BILLING_POST_IDEMPOTENCY_KEY = "billing:post_idempotency:{key}"


def billing_transaction_key(transaction_uuid: str) -> str:
    return BILLING_TRANSACTION_KEY.format(uuid=transaction_uuid)


def billing_project_spending_limit_key(org_id: str, project_id: int) -> str:
    return BILLING_PROJECT_SPENDING_LIMIT_KEY.format(
        org_id=org_id, project_id=project_id
    )


def billing_org_spending_limit_key(org_id: str) -> str:
    return BILLING_ORG_SPENDING_LIMIT_KEY.format(org_id=org_id)


def billing_org_usage_key(org_id: str, period: str) -> str:
    return BILLING_ORG_USAGE_KEY.format(org_id=org_id, period=period)


def billing_project_usage_key(org_id: str, project_id: int, period: str) -> str:
    return BILLING_PROJECT_USAGE_KEY.format(
        org_id=org_id, project_id=project_id, period=period
    )


def billing_post_idempotency_key(key: str) -> str:
    return BILLING_POST_IDEMPOTENCY_KEY.format(key=key)
