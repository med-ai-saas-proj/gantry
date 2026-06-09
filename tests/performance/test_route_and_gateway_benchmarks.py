from __future__ import annotations

import pytest

from gantry.api_gateway.routes import _inject_api_key_context_headers, filter_headers
from tests.api.fakes import api_key_info_payload
from tests.performance.helpers import gateway_headers_payload

pytestmark = [pytest.mark.performance, pytest.mark.timeout(30)]


def test_gateway_header_filter_latency(benchmark) -> None:
    headers = gateway_headers_payload()

    result = benchmark(lambda: filter_headers(headers))

    assert result == {
        "X-Trace": "trace-1",
        "X-Client": "client-1",
        "X-Request-ID": "request-1",
    }


def test_gateway_api_key_context_header_generation_latency(benchmark) -> None:
    api_key_info = api_key_info_payload()

    result = benchmark(lambda: _inject_api_key_context_headers(api_key_info))

    assert result["X-API-Key-UUID"] == "api-key-1"
    assert result["X-Organization-UUID"] == "org-1"
    assert result["X-RPM-Limit-Project"] == "500"

