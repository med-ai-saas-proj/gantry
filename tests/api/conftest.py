from __future__ import annotations

import pytest

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
from gantry.service.conversation.factories import (
    getSequenceConversationService,
    getTreeConversationService,
)
from gantry.service.file_storage.factories import getFileStorageService
from gantry.service.ai_gateway.factories import getAiGatewayService
from gantry.service.rag.factories import getRagService

from tests.api.fakes import (
    FakeAdminService,
    FakeAiGatewayService,
    FakeApiKeyService,
    FakeBillingAggregateQueryService,
    FakeBillingSourceService,
    FakeBillingTransactionService,
    FakeConversationService,
    FakeSequenceConversationService,
    FakeTreeConversationService,
    FakeCreditService,
    FakeFileStorageService,
    FakeGatewayService,
    FakeInvoiceService,
    FakeLogQueryService,
    FakeOrgService,
    FakeProjectService,
    FakeRagService,
)


@pytest.fixture
def fake_project_service() -> FakeProjectService:
    return FakeProjectService()


@pytest.fixture
def fake_api_key_service() -> FakeApiKeyService:
    return FakeApiKeyService()


@pytest.fixture
def fake_org_service() -> FakeOrgService:
    return FakeOrgService()


@pytest.fixture
def fake_admin_service() -> FakeAdminService:
    return FakeAdminService()


@pytest.fixture
def fake_billing_aggregate_service() -> FakeBillingAggregateQueryService:
    return FakeBillingAggregateQueryService()


@pytest.fixture
def fake_billing_source_service() -> FakeBillingSourceService:
    return FakeBillingSourceService()


@pytest.fixture
def fake_credit_service() -> FakeCreditService:
    return FakeCreditService()


@pytest.fixture
def fake_invoice_service() -> FakeInvoiceService:
    return FakeInvoiceService()


@pytest.fixture
def fake_billing_transaction_service() -> FakeBillingTransactionService:
    return FakeBillingTransactionService()


@pytest.fixture
def fake_log_query_service() -> FakeLogQueryService:
    return FakeLogQueryService()


@pytest.fixture
def fake_file_storage_service() -> FakeFileStorageService:
    return FakeFileStorageService()


@pytest.fixture
def fake_rag_service() -> FakeRagService:
    return FakeRagService()


@pytest.fixture
def fake_conversation_service() -> FakeConversationService:
    return FakeConversationService()


@pytest.fixture
def fake_sequence_conversation_service() -> FakeSequenceConversationService:
    return FakeSequenceConversationService()


@pytest.fixture
def fake_tree_conversation_service() -> FakeTreeConversationService:
    return FakeTreeConversationService()


@pytest.fixture
def fake_gateway_service() -> FakeGatewayService:
    return FakeGatewayService()


@pytest.fixture
def fake_ai_gateway_service() -> FakeAiGatewayService:
    return FakeAiGatewayService()


@pytest.fixture
def authenticated_api(
    override_dependencies,
    fake_user_info,
    fake_admin_info,
    fake_project_service,
    fake_api_key_service,
    fake_org_service,
    fake_admin_service,
    fake_billing_aggregate_service,
    fake_billing_source_service,
    fake_credit_service,
    fake_invoice_service,
    fake_billing_transaction_service,
    fake_log_query_service,
    mocker,
):
    override_dependencies[getUserInfo] = lambda: fake_user_info
    override_dependencies[getAdminInfo] = lambda: fake_admin_info
    override_dependencies[getProjectService] = lambda: fake_project_service
    override_dependencies[getApiKeyService] = lambda: fake_api_key_service
    override_dependencies[getOrgService] = lambda: fake_org_service
    override_dependencies[getAdminService] = lambda: fake_admin_service
    override_dependencies[getBillingAggregateQueryService] = lambda: fake_billing_aggregate_service
    override_dependencies[getBillingSourceService] = lambda: fake_billing_source_service
    override_dependencies[getCreditService] = lambda: fake_credit_service
    override_dependencies[getInvoiceService] = lambda: fake_invoice_service
    override_dependencies[getBillingTransactionService] = lambda: fake_billing_transaction_service

    import gantry.management.billing.routers.aggregate_query as aggregate_routes
    import gantry.management.billing.routers.transactions as transaction_routes
    import gantry.management.logging.routers as logging_routes

    mocker.patch.object(
        aggregate_routes,
        "getProjectService",
        return_value=fake_project_service,
    )
    mocker.patch.object(
        transaction_routes,
        "getProjectService",
        return_value=fake_project_service,
    )
    mocker.patch.object(logging_routes, "log_query_service", fake_log_query_service)
    return {
        "project": fake_project_service,
        "api_key": fake_api_key_service,
        "org": fake_org_service,
        "admin": fake_admin_service,
        "billing_aggregate": fake_billing_aggregate_service,
        "billing_source": fake_billing_source_service,
        "credit": fake_credit_service,
        "invoice": fake_invoice_service,
        "billing_transaction": fake_billing_transaction_service,
        "logging": fake_log_query_service,
    }


@pytest.fixture
def authenticated_service_api(
    service_override_dependencies,
    fake_user_info,
    fake_api_key_info,
    fake_project_service,
    fake_api_key_service,
    fake_file_storage_service,
    fake_rag_service,
    fake_sequence_conversation_service,
    fake_tree_conversation_service,
):
    service_override_dependencies[getUserInfo] = lambda: fake_user_info
    service_override_dependencies[getApiKeyInfo] = lambda: fake_api_key_info
    service_override_dependencies[getProjectService] = lambda: fake_project_service
    service_override_dependencies[getApiKeyService] = lambda: fake_api_key_service
    service_override_dependencies[getFileStorageService] = lambda: fake_file_storage_service
    service_override_dependencies[getRagService] = lambda: fake_rag_service
    service_override_dependencies[getSequenceConversationService] = lambda: fake_sequence_conversation_service
    service_override_dependencies[getTreeConversationService] = lambda: fake_tree_conversation_service
    return {
        "project": fake_project_service,
        "api_key": fake_api_key_service,
        "file_storage": fake_file_storage_service,
        "rag": fake_rag_service,
        "sequence_conversation": fake_sequence_conversation_service,
        "tree_conversation": fake_tree_conversation_service,
    }


@pytest.fixture
def authenticated_gateway_api(
    gateway_override_dependencies,
    fake_api_key_info,
    fake_gateway_service,
):
    gateway_override_dependencies[getApiKeyInfo] = lambda: fake_api_key_info
    gateway_override_dependencies[getApiGatewayService] = lambda: fake_gateway_service
    return {"gateway": fake_gateway_service}


@pytest.fixture
def authenticated_internal_api(
    internal_override_dependencies,
    fake_admin_info,
    fake_api_key_info,
    fake_api_key_service,
    fake_credit_service,
    fake_invoice_service,
    fake_billing_transaction_service,
    fake_ai_gateway_service,
):
    internal_override_dependencies[getAdminInfo] = lambda: fake_admin_info
    internal_override_dependencies[getApiKeyInfo] = lambda: fake_api_key_info
    internal_override_dependencies[getApiKeyService] = lambda: fake_api_key_service
    internal_override_dependencies[getCreditService] = lambda: fake_credit_service
    internal_override_dependencies[getInvoiceService] = lambda: fake_invoice_service
    internal_override_dependencies[getBillingTransactionService] = lambda: fake_billing_transaction_service
    internal_override_dependencies[getAiGatewayService] = lambda: fake_ai_gateway_service
    return {
        "api_key": fake_api_key_service,
        "credit": fake_credit_service,
        "invoice": fake_invoice_service,
        "billing_transaction": fake_billing_transaction_service,
        "ai_gateway": fake_ai_gateway_service,
    }
