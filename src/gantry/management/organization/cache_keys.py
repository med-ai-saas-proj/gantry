"""Shared Redis cache-key helpers for organization settings."""

ORG_RPM_LIMIT_CACHE_TTL_SECONDS = 36000
BILLING_CACHE_TTL_SECONDS = 3600  # 1 hour
ORG_RPM_LIMIT_KEY = "organization:rpm_limit:{org_id}"
BILLING_ORG_SPENDING_LIMIT_KEY = "billing:spending_limit:{org_id}"
PROJECT_RPM_LIMIT_KEY = "organization:rpm_limit:{org_id}:proj:{project_id}"


def organization_rpm_limit_key(org_id: str) -> str:
    """Build the Redis key for one organization's RPM limit."""
    return ORG_RPM_LIMIT_KEY.format(org_id=org_id)


def project_rpm_limit_key(org_id: str, project_id: int) -> str:
    """Build the Redis key for one project's RPM limit."""
    return PROJECT_RPM_LIMIT_KEY.format(org_id=org_id, project_id=project_id)


def billing_org_spending_limit_key(org_id: str) -> str:
    return BILLING_ORG_SPENDING_LIMIT_KEY.format(org_id=org_id)
