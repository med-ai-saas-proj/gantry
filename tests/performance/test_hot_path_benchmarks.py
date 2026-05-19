from __future__ import annotations

import pytest

from gantry.management.api_key.services import ApiKeyService
from gantry.shared.utils.permission_utils import (
    normalize_project_permission_map,
    serialize_project_permission_values,
)
from tests.performance.helpers import (
    project_permission_payload,
    scaled_amount_roundtrip,
    serialized_permission_payload,
)

pytestmark = [pytest.mark.performance, pytest.mark.timeout(30)]


def _api_key_service_for_hash() -> ApiKeyService:
    service = object.__new__(ApiKeyService)
    service.key_secret = "benchmark-secret"
    return service


def test_project_permission_normalization_latency(benchmark) -> None:
    raw = project_permission_payload(200)

    result = benchmark(normalize_project_permission_map, raw)

    assert len(result) == 200
    assert result["project-0"] == ["project.settings.read", "apikey.read"]


def test_project_permission_serialization_latency(benchmark) -> None:
    permissions = serialized_permission_payload(100)

    result = benchmark(serialize_project_permission_values, permissions)

    assert len(result) == 100


def test_api_key_parse_and_hint_latency(benchmark) -> None:
    key = "sk_api-key-uuid.secret-value"

    def parse_and_hint() -> tuple[object, str]:
        return ApiKeyService._internalGetApiKeyParts(key), ApiKeyService.generateHint(key)

    result, hint = benchmark(parse_and_hint)

    assert result.unwrap() == ("api-key-uuid", "secret-value")
    assert hint == "sk_ap...alue"


def test_api_key_hash_latency(benchmark) -> None:
    service = _api_key_service_for_hash()

    digest = benchmark(service._hashApiKey, "sk_api-key-uuid.secret-value")

    assert len(digest) == 64


def test_scaled_amount_conversion_latency(benchmark) -> None:
    result = benchmark(scaled_amount_roundtrip)

    assert str(result[2]) == "12.34567891"
