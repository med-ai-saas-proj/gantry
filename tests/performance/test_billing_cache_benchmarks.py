from __future__ import annotations

import pytest

from tests.performance.helpers import all_billing_cache_keys, billing_period_roundtrip

pytestmark = [pytest.mark.performance, pytest.mark.timeout(30)]


def test_billing_cache_key_generation_latency(benchmark) -> None:
    result = benchmark(lambda: [all_billing_cache_keys() for _ in range(100)])

    assert len(result) == 100
    assert result[0][0].startswith("billing:trx:")
    assert "spending_limit" in result[0][1]


def test_billing_period_helper_latency(benchmark) -> None:
    current, next_period, previous_period = benchmark(billing_period_roundtrip)

    assert current.month == 5
    assert next_period.month == 6
    assert previous_period.month == 4
