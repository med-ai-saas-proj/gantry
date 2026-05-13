from __future__ import annotations

import httpx
import pytest
import respx

from gantry.api_gateway.service import (
    InsufficientPermission,
    RouteNotFoundError,
)
from gantry.management.api_key.services import (
    ApiKeyNotFoundError,
    InvalidPermissionError as InvalidApiKeyPermissionError,
)
from gantry.management.billing.services.billing_source_service import (
    BillingSourceAlreadyExistsError,
    BillingSourceNotFoundError,
)
from gantry.management.billing.services.invoice_service import InvoiceNotFoundError
from gantry.management.billing.services.transaction_services import (
    SpendingLimitExceeded,
    TransactionNotFound,
    TransactionNotFoundOrExpiredOrCaptured,
)
from gantry.management.organization.services import (
    DeletionAlreadyRequestedError,
    DeletionRequestNotFoundError,
    InvalidPermissionError as InvalidOrgPermissionError,
    ReadOwnPermissionsOrManageRequiredError,
    UserAlreadyInOrganizationError,
)
from gantry.management.project.services import (
    InsufficientProjectPermissionError,
    InvalidProjectPermissionError,
    ProjectArchivedError,
    ProjectNotFoundError,
    UserAlreadyInProjectError,
    UserNotInProjectError,
)
from gantry.service.file_storage.services import FileNotFoundInSystemError
from gantry.service.rag.services import (
    InvalidEmbeddingDimensionError,
    TaskNotFoundError,
)
from tests.api.fakes import (
    CONVERSATION_UUID,
    FILE_UUID,
    INVOICE_UUID,
    PROJECT_UUID,
    TRANSACTION_UUID,
)
from tests.helpers.http import assert_error_response

pytestmark = pytest.mark.api

AUTH = {"Authorization": "Bearer test-token"}
SERVICE_AUTH = {"Authorization": "Bearer user-token", "X-Api-Key": "sk_test"}
INTERNAL_AUTH = {"Authorization": "Bearer admin-token", "X-Api-Key": "sk_test"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "request_method", "path", "error", "expected_status", "body"),
    [
        ("getOrgInfo", "GET", "/v1/organizations/org-1", DeletionRequestNotFoundError(), 404, None),
        ("updateOrgInfo", "PATCH", "/v1/organizations/org-1", InvalidOrgPermissionError(), 400, {"name": "Org"}),
        ("requestDeleteOrg", "DELETE", "/v1/organizations/org-1", DeletionAlreadyRequestedError(), 409, None),
        ("getUsers", "GET", "/v1/organizations/org-1/users", UserAlreadyInOrganizationError(), 409, None),
        ("getUserPermissions", "GET", "/v1/organizations/org-1/users/user-2/permissions", ReadOwnPermissionsOrManageRequiredError(), 403, None),
    ],
)
async def test_organization_domain_errors_are_mapped_to_http_problem_details(
    api_client,
    authenticated_api,
    method_name: str,
    request_method: str,
    path: str,
    error: Exception,
    expected_status: int,
    body: dict | None,
) -> None:
    authenticated_api["org"].fail_next(method_name, error)

    response = await api_client.request(
        request_method,
        path,
        headers=AUTH,
        json=body,
    )

    payload = assert_error_response(response, expected_status)
    assert payload["status"] == expected_status


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "request_method", "path", "error", "expected_status", "body"),
    [
        ("getProject", "GET", f"/v1/projects/{PROJECT_UUID}", ProjectNotFoundError(), 404, None),
        ("updateProject", "PUT", f"/v1/projects/{PROJECT_UUID}", ProjectArchivedError(), 409, {"name": "P", "description": "D"}),
        ("listProjectUsers", "GET", f"/v1/projects/{PROJECT_UUID}/users", InsufficientProjectPermissionError(), 403, None),
        ("addUserToProject", "POST", f"/v1/projects/{PROJECT_UUID}/users", UserAlreadyInProjectError(), 409, {"user_id": "user-2"}),
        ("removeUserFromProject", "DELETE", f"/v1/projects/{PROJECT_UUID}/users/user-2", UserNotInProjectError(), 404, None),
        ("updateUserPermissions", "PUT", f"/v1/projects/{PROJECT_UUID}/users/user-2/permissions", InvalidProjectPermissionError(), 400, {"permissions": ["bad.permission"]}),
    ],
)
async def test_project_domain_errors_are_mapped_to_http_problem_details(
    api_client,
    authenticated_api,
    method_name: str,
    request_method: str,
    path: str,
    error: Exception,
    expected_status: int,
    body: dict | None,
) -> None:
    authenticated_api["project"].fail_next(method_name, error)

    response = await api_client.request(
        request_method,
        path,
        headers=AUTH,
        json=body,
    )

    assert_error_response(response, expected_status)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "request_method", "path", "error", "expected_status", "body", "params"),
    [
        ("getApiKey", "GET", "/v1/api-keys/api-key-1", ApiKeyNotFoundError(), 404, None, None),
        ("createApiKey", "POST", "/v1/api-keys", InvalidApiKeyPermissionError(), 400, {"name": "K", "description": "D", "permissions": ["bad.permission"]}, {"project_id": PROJECT_UUID}),
        ("updateApiKey", "PUT", "/v1/api-keys/api-key-1", InvalidApiKeyPermissionError(), 400, {"name": "K", "description": "D", "permissions": ["bad.permission"]}, None),
        ("deleteApiKey", "DELETE", "/v1/api-keys/api-key-1", ApiKeyNotFoundError(), 404, None, None),
    ],
)
async def test_api_key_domain_errors_are_mapped_to_http_problem_details(
    api_client,
    authenticated_api,
    method_name: str,
    request_method: str,
    path: str,
    error: Exception,
    expected_status: int,
    body: dict | None,
    params: dict | None,
) -> None:
    authenticated_api["api_key"].fail_next(method_name, error)

    response = await api_client.request(
        request_method,
        path,
        headers=AUTH,
        params=params,
        json=body,
    )

    assert_error_response(response, expected_status)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("service_key", "method_name", "request_method", "path", "error", "expected_status", "body"),
    [
        ("billing_source", "createBillingSource", "POST", "/v1/billing/sources", BillingSourceAlreadyExistsError("exists"), 400, {"name": "Billing User", "email": "billing@example.com", "phone": "+10000000000", "address": {"line1": "1 Main", "line2": "Suite 1", "city": "HCM", "state": "HCM", "postal_code": "70000", "country": "VN"}, "provider": "stripe"}),
        ("billing_source", "getBillingSource", "GET", "/v1/billing/sources", BillingSourceNotFoundError("missing"), 404, None),
        ("invoice", "getInvoiceById", "GET", f"/v1/billing/invoices/{INVOICE_UUID}", InvoiceNotFoundError(), 404, None),
        ("billing_transaction", "getTransactionById", "GET", f"/v1/billing/transactions/{TRANSACTION_UUID}", TransactionNotFound(), 404, None),
    ],
)
async def test_management_billing_domain_errors_are_mapped_to_http_problem_details(
    api_client,
    authenticated_api,
    service_key: str,
    method_name: str,
    request_method: str,
    path: str,
    error: Exception,
    expected_status: int,
    body: dict | None,
) -> None:
    authenticated_api[service_key].fail_next(method_name, error)

    response = await api_client.request(request_method, path, headers=AUTH, json=body)

    assert_error_response(response, expected_status)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("service_key", "method_name", "request_method", "path", "error", "expected_status", "body"),
    [
        ("file_storage", "getFileInfo", "GET", f"/v1/file-storage/service/{FILE_UUID}/info", FileNotFoundInSystemError(), 404, None),
        ("file_storage", "deleteFile", "DELETE", f"/v1/file-storage/service/{FILE_UUID}", FileNotFoundInSystemError(), 404, None),
        ("rag", "getTaskStatus", "GET", "/v1/rag/service/files/task-1", TaskNotFoundError(), 404, None),
        ("rag", "querySimilarByVector", "POST", "/v1/rag/service/query/vector", InvalidEmbeddingDimensionError(), 400, {"embedding": [0.1], "top_k": 3}),
        ("conversation", "getConversationMetadata", "GET", f"/v1/conversations/{CONVERSATION_UUID}", ProjectNotFoundError(), 404, None),
    ],
)
async def test_service_domain_errors_are_mapped_to_http_problem_details(
    service_client,
    authenticated_service_api,
    service_key: str,
    method_name: str,
    request_method: str,
    path: str,
    error: Exception,
    expected_status: int,
    body: dict | None,
) -> None:
    authenticated_service_api[service_key].fail_next(method_name, error)

    response = await service_client.request(request_method, path, headers=SERVICE_AUTH, json=body)

    assert_error_response(response, expected_status)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("service_key", "method_name", "request_method", "path", "error", "expected_status", "body"),
    [
        ("billing_transaction", "post", "POST", "/billing/", SpendingLimitExceeded(), 403, {"amount": {"value": 1234, "scale": 2}, "details": {"usage": 1}, "capture": False}),
        ("billing_transaction", "capture", "POST", f"/billing/{TRANSACTION_UUID}/capture", TransactionNotFoundOrExpiredOrCaptured(), 400, {"real_amount": {"value": 1234, "scale": 2}}),
        ("invoice", "getInvoiceByIdForAdmin", "GET", f"/billing/invoices/{INVOICE_UUID}", InvoiceNotFoundError(), 404, None),
    ],
)
async def test_internal_billing_domain_errors_are_mapped_to_http_problem_details(
    internal_client,
    authenticated_internal_api,
    service_key: str,
    method_name: str,
    request_method: str,
    path: str,
    error: Exception,
    expected_status: int,
    body: dict | None,
) -> None:
    authenticated_internal_api[service_key].fail_next(method_name, error)

    response = await internal_client.request(request_method, path, headers=INTERNAL_AUTH, json=body)

    assert_error_response(response, expected_status)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "error", "expected_status"),
    [
        ("getDestination", RouteNotFoundError(), 404),
        ("checkPermission", InsufficientPermission(), 403),
    ],
)
async def test_gateway_domain_errors_are_mapped_to_http_problem_details(
    gateway_client,
    authenticated_gateway_api,
    method_name: str,
    error: Exception,
    expected_status: int,
) -> None:
    authenticated_gateway_api["gateway"].fail_next(method_name, error)

    response = await gateway_client.get("/chat/v1/messages", headers={"X-Api-Key": "sk_test"})

    assert_error_response(response, expected_status)


@pytest.mark.asyncio
async def test_gateway_upstream_failure_is_documented_as_non_success_contract(
    gateway_client,
    authenticated_gateway_api,
) -> None:
    with respx.mock(assert_all_called=True) as router:
        router.get("https://upstream.example/base/v1/messages").mock(
            side_effect=httpx.ConnectError("upstream unavailable")
        )
        with pytest.raises(httpx.ConnectError):
            await gateway_client.get(
                "/chat/v1/messages",
                headers={"X-Api-Key": "sk_test"},
            )

    # ASGITransport currently re-raises uncaught upstream httpx errors.
    # Keep this explicit until gateway maps it to GatewayUpstreamError.
