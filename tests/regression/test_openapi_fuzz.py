from __future__ import annotations

from contextlib import nullcontext

import pytest
import httpx
import respx
import schemathesis
from hypothesis import HealthCheck, given, settings

from gantry.api_gateway.factories import getApiGatewayService
from gantry.management.admin.factories import getAdminService
from gantry.management.api_key.dependencies import getApiKeyInfo
from gantry.management.api_key.factories import getApiKeyService
from gantry.management.auth.dependencies import getAdminInfo, getUserInfo
from gantry.management.billing.factories import (
    getBillingAggregateQueryService,
    getBillingSourceService,
    getBillingTransactionService,
    getCreditService,
    getInvoiceService,
)
from gantry.management.organization.factories import getOrgService
from gantry.management.project.factories import getProjectService
from gantry.service.ai_gateway.factories import getAiGatewayService
from gantry.service.conversation.factories import (
    getSequenceConversationService,
    getTreeConversationService,
)
from gantry.service.file_storage.factories import getFileStorageService
from gantry.service.rag.factories import getRagService
from tests.api.fakes import (
    FakeAdminService,
    FakeAiGatewayService,
    FakeApiKeyService,
    FakeBillingAggregateQueryService,
    FakeBillingSourceService,
    FakeBillingTransactionService,
    FakeCreditService,
    FakeFileStorageService,
    FakeGatewayService,
    FakeInvoiceService,
    FakeOrgService,
    FakeProjectService,
    FakeRagService,
    FakeSequenceConversationService,
    FakeTreeConversationService,
)
from tests.factories import AdminInfoFactory, ApiKeyInfoFactory, UserInfoFactory
from tests.regression.helpers import assert_no_unexpected_5xx

pytestmark = pytest.mark.regression

FUZZ_SAMPLE_LIMIT = 8


def _schema_for(app_name: str, request):
    app = request.getfixturevalue(f"{app_name}_app")
    _install_fake_dependencies(app)
    openapi = request.getfixturevalue(f"{app_name}_openapi")
    schema = schemathesis.openapi.from_dict(openapi)
    schema.app = app
    return schema


def _install_fake_dependencies(app) -> None:
    """Keep fuzz ASGI calls no-Docker/no-network by replacing real services."""
    app.dependency_overrides[getUserInfo] = lambda: UserInfoFactory()
    app.dependency_overrides[getAdminInfo] = lambda: AdminInfoFactory()
    app.dependency_overrides[getApiKeyInfo] = lambda: ApiKeyInfoFactory()
    app.dependency_overrides[getProjectService] = FakeProjectService
    app.dependency_overrides[getApiKeyService] = FakeApiKeyService
    app.dependency_overrides[getOrgService] = FakeOrgService
    app.dependency_overrides[getAdminService] = FakeAdminService
    app.dependency_overrides[getBillingAggregateQueryService] = (
        FakeBillingAggregateQueryService
    )
    app.dependency_overrides[getBillingSourceService] = FakeBillingSourceService
    app.dependency_overrides[getBillingTransactionService] = (
        FakeBillingTransactionService
    )
    app.dependency_overrides[getCreditService] = FakeCreditService
    app.dependency_overrides[getInvoiceService] = FakeInvoiceService
    app.dependency_overrides[getFileStorageService] = FakeFileStorageService
    app.dependency_overrides[getRagService] = FakeRagService
    app.dependency_overrides[getSequenceConversationService] = (
        FakeSequenceConversationService
    )
    app.dependency_overrides[getTreeConversationService] = (
        FakeTreeConversationService
    )
    app.dependency_overrides[getApiGatewayService] = FakeGatewayService
    app.dependency_overrides[getAiGatewayService] = FakeAiGatewayService


def _safe_read_operations(schema, limit: int | None = FUZZ_SAMPLE_LIMIT):
    operations = [
        operation
        for result in schema.get_all_operations()
        if (operation := result.ok()).method == "get"
    ]
    if limit is None:
        return operations
    return operations[:limit]


def _auth_headers(app_name: str) -> dict[str, str]:
    headers = {
        "Authorization": "Bearer regression-token",
        "X-Api-Key": "sk_regression",
        "stripe-signature": "invalid",
    }
    if app_name == "gateway":
        return {"X-Api-Key": "sk_regression"}
    return headers


def _call_case_asserting_no_unexpected_5xx(case, **kwargs) -> None:
    try:
        response = case.call(**kwargs)
    except Exception as exc:
        status = getattr(exc, "status", None)
        if isinstance(status, int) and status < 500:
            return
        raise
    assert_no_unexpected_5xx(response)


@pytest.mark.order(3)
@pytest.mark.parametrize(
    "app_name",
    ["management", "service", "gateway", "internal"],
)
def test_schemathesis_safe_read_cases_do_not_return_unexpected_5xx(
    request,
    app_name: str,
) -> None:
    schema = _schema_for(app_name, request)
    upstream_mock = respx.mock(assert_all_called=False)
    context = upstream_mock if app_name == "gateway" else nullcontext()
    with context:
        if app_name == "gateway":
            upstream_mock.route(url__regex=r"https://upstream\.example/.*").mock(
                return_value=httpx.Response(
                    200,
                    json={"ok": True},
                    headers={"Content-Type": "application/json"},
                )
            )
        for operation in _safe_read_operations(schema):
            case = operation.as_strategy().example()
            _call_case_asserting_no_unexpected_5xx(
                case,
                base_url="http://testserver",
                headers=_auth_headers(app_name),
            )


@pytest.mark.order(3)
def test_schemathesis_fuzzes_public_management_read_without_5xx(request) -> None:
    schema = _schema_for("management", request)
    operation = next(
        operation
        for operation in _safe_read_operations(schema, limit=None)
        if "security" not in operation.definition.raw
    )

    @given(case=operation.as_strategy())
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def _run(case) -> None:
        _call_case_asserting_no_unexpected_5xx(
            case,
            base_url="http://testserver",
        )

    _run()
