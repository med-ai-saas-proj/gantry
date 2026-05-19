from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from gantry.management.billing.cache_settings import (
    billing_org_spending_limit_key,
    billing_org_usage_key,
    billing_post_idempotency_key,
    billing_project_spending_limit_key,
    billing_project_usage_key,
    billing_transaction_key,
)
from gantry.management.billing.utils import (
    get_billing_period,
    get_next_billing_period,
    get_previous_billing_period,
)
from gantry.shared.utils.scaled_amount import (
    decimal_to_scaled_int,
    int_to_scaled_int,
    scaled_int_to_decimal,
)
from tests.helpers.routes import sample_path


ORG_ID = "org-benchmark"
PROJECT_ID = 42
PROJECT_UUID = "11111111-1111-1111-1111-111111111111"
API_KEY_UUID = "22222222-2222-2222-2222-222222222222"
TRANSACTION_UUID = "33333333-3333-3333-3333-333333333333"
PERIOD = "2026-05"


def project_permission_payload(projects: int = 200) -> list[dict[str, list[str]]]:
    return [
        {
            f"project-{index}": [
                "project.settings.read",
                "apikey.read",
                "apikey.read",
                "",
            ]
        }
        for index in range(projects)
    ]


def serialized_permission_payload(projects: int = 100) -> dict[str, list[str]]:
    return {
        f"project-{index}": [
            "project.read",
            "project.settings.read",
            "apikey.read",
        ]
        for index in range(projects)
    }


def gateway_headers_payload() -> dict[str, str]:
    return {
        "Connection": "keep-alive",
        "Content-Length": "10",
        "Host": "example.test",
        "X-Trace": "trace-1",
        "X-Client": "client-1",
        "X-Request-ID": "request-1",
    }


def all_billing_cache_keys() -> list[str]:
    return [
        billing_transaction_key(TRANSACTION_UUID),
        billing_project_spending_limit_key(ORG_ID, PROJECT_ID),
        billing_org_spending_limit_key(ORG_ID),
        billing_org_usage_key(ORG_ID, PERIOD),
        billing_project_usage_key(ORG_ID, PROJECT_ID, PERIOD),
        billing_post_idempotency_key("idem-1"),
    ]


def billing_period_roundtrip() -> tuple[datetime, datetime, datetime]:
    current = get_billing_period(datetime(2026, 5, 12, 13, 45, 30, tzinfo=UTC))
    return current, get_next_billing_period(current), get_previous_billing_period(current)


def scaled_amount_roundtrip() -> tuple[int, int, Decimal]:
    return (
        int_to_scaled_int(123, 8),
        decimal_to_scaled_int(Decimal("12.34567891"), 8),
        scaled_int_to_decimal(1234567891, 8),
    )


def sample_management_paths(paths: list[str]) -> list[str]:
    return [sample_path(path) for path in paths]
