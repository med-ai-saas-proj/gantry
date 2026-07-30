from gantry.settings import AppStage, getAppSettings
from gantry.shared.health import setup_health_routes
from gantry.management.api_key import ApiKeyInfo, getApiKeyInfo
from gantry.management.billing import (
    PostRequest,
    TransactionService,
    getBillingTransactionService,
)
from gantry.shared.logging.logger import getServiceLogger
from gantry.shared.utils.uuid_utils import uuid7

from .service import ApiGatewayService
from .settings import getApiGatewaySettings
from .factories import getApiGatewayService

import json
from uuid import UUID
from typing import Optional, Annotated
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from fastapi import Path, Depends, FastAPI, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware


gateway_app = FastAPI(
    debug=getAppSettings().stage == AppStage.DEV, redirect_slashes=False
)

setup_health_routes(gateway_app)

gateway_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "content-encoding",
}

INFO_HEADERS = {
    "x-organization-uuid",
    "x-project-uuid",
    "x-api-key-uuid",
    "x-permissions",
    "x-rpm-limit-organization",
    "x-rpm-limit-project",
    "x-spending-limit-organization",
    "x-spending-limit-project",
}


def filter_headers(headers: dict[str, str]) -> dict[str, str]:
    """Remove hop-by-hop headers + auto-calculated ones."""
    return {
        k: v
        for k, v in headers.items()
        if k.lower() not in HOP_BY_HOP_HEADERS and k.lower() not in INFO_HEADERS
    }


def _inject_api_key_context_headers(
    api_key_info: ApiKeyInfo,
) -> dict[str, str]:
    # headers["X-Organization-UUID"] = api_key_info["organization_uuid"]
    # headers["X-Project-UUID"] = api_key_info["project_uuid"]
    # headers["X-API-Key-UUID"] = api_key_info["api_key_uuid"]
    # headers["X-Permissions"] = json.dumps(api_key_info["permissions"])
    # headers["X-RPM-Limit-Organization"] = str(
    #     api_key_info["rpm_limit_organization"]
    # )
    # headers["X-RPM-Limit-Project"] = str(api_key_info["rpm_limit_project"])
    # headers["X-Spending-Limit-Organization"] = str(
    #     api_key_info["spending_limit_organization"]
    # )
    # headers["X-Spending-Limit-Project"] = str(
    #     api_key_info["spending_limit_project"]
    # )
    headers = {
        "X-Organization-UUID": api_key_info["organization_uuid"],
        "X-Project-UUID": api_key_info["project_uuid"],
        "X-API-Key-UUID": api_key_info["api_key_uuid"],
        "X-Permissions": json.dumps(api_key_info["permissions"]),
        "X-RPM-Limit-Organization": str(api_key_info["rpm_limit_organization"]),
        "X-RPM-Limit-Project": str(api_key_info["rpm_limit_project"]),
        "X-Spending-Limit-Organization": str(
            api_key_info["spending_limit_organization"]
        ),
        "X-Spending-Limit-Project": str(api_key_info["spending_limit_project"]),
    }
    return headers


@gateway_app.api_route(
    "/{route_name}/{full_path:path}/",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@gateway_app.api_route(
    "/{route_name}/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def gateway_proxy_with_path(
    route_name: Annotated[str, Path()],
    full_path: Annotated[str | None, Path()],
    request: Request,
    apikey_info: Annotated[ApiKeyInfo, Depends(getApiKeyInfo)],
    gateway_service: Annotated[
        ApiGatewayService, Depends(getApiGatewayService)
    ],
    transaction_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
    background_tasks: BackgroundTasks,
):
    return await _gateway_proxy(
        route_name,
        request,
        apikey_info,
        full_path,
        gateway_service,
        transaction_service,
        background_tasks,
    )


@gateway_app.api_route(
    "/{route_name}/",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@gateway_app.api_route(
    "/{route_name}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def gateway_proxy(
    route_name: Annotated[str, Path()],
    request: Request,
    apikey_info: Annotated[ApiKeyInfo, Depends(getApiKeyInfo)],
    gateway_service: Annotated[
        ApiGatewayService, Depends(getApiGatewayService)
    ],
    transaction_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
    background_tasks: BackgroundTasks,
):
    return await _gateway_proxy(
        route_name,
        request,
        apikey_info,
        None,
        gateway_service,
        transaction_service,
        background_tasks,
    )


async def _gateway_proxy(
    route_name: str,
    request: Request,
    apikey_info: ApiKeyInfo,
    full_path: Optional[str],
    gateway_service: ApiGatewayService,
    transaction_service: TransactionService,
    background_tasks: BackgroundTasks,
):
    # print(f"Incoming request for route: {route_name}, full_path: {full_path}")
    destination = gateway_service.getDestination(route_name=route_name).unwrap()
    gateway_service.checkPermission(
        apikey_info["permissions"], destination
    ).unwrap()

    key = uuid7()
    transaction_uuid = None
    if destination.auto_charge is not None:
        result = await transaction_service.post(
            str(key),
            PostRequest(
                api_key_uuid=UUID(apikey_info["api_key_uuid"]),
                service_name=route_name,
                amount=destination.auto_charge,
            ),
        )
        transaction_uuid = result.unwrap()

    incoming_headers = filter_headers(dict(request.headers))
    incoming_headers.update(_inject_api_key_context_headers(apikey_info))

    original_host = request.headers.get("host", "")
    incoming_headers["X-Forwarded-Host"] = original_host
    incoming_headers["X-Forwarded-Proto"] = request.url.scheme
    incoming_headers["X-Forwarded-For"] = (
        request.client.host if request.client else ""
    )

    request_timeout = getApiGatewaySettings().request_timeout.total_seconds()
    client = httpx.AsyncClient(timeout=request_timeout)

    full_url = urljoin(
        destination.address.encoded_string(),
        full_path,
    )

    original_path = request.url.path
    has_trailing_slash = original_path.endswith("/")

    if has_trailing_slash and not full_url.endswith("/"):
        full_url += "/"
    if not has_trailing_slash and full_url.endswith("/"):
        full_url = full_url.rstrip("/")

    req = client.build_request(
        method=request.method,
        url=full_url,
        headers=incoming_headers,
        content=request.stream(),
        params=request.query_params,
    )
    response = await client.send(request=req, stream=True)
    response_headers = filter_headers(dict(response.headers))

    if (
        300 <= response.status_code < 400
        and "location" in response_headers
        and destination.proxy_redirect
    ):
        original_location = response_headers["location"]
        for original, redirect in destination.proxy_redirect.items():
            if original_location.startswith(original):
                new_location = original_location.replace(original, redirect, 1)
                response_headers["location"] = new_location
                break

    getServiceLogger(
        org_id=apikey_info["organization_uuid"],
        project_id=apikey_info["project_uuid"],
    ).info(
        "api_gateway",
        route_name=route_name,
        full_path=full_path,
        method=request.method,
        status_code=response.status_code,
        # headers=incoming_headers,
        api_key_id=apikey_info["api_key_uuid"],
        media_type=response.headers.get("Content-Type"),
    )

    async def capture():
        if destination.auto_charge is not None and transaction_uuid is not None:
            (
                await transaction_service.capture(
                    transaction_uuid, destination.auto_charge
                )
            ).unwrap()

    background_tasks.add_task(capture)
    background_tasks.add_task(client.aclose)
    return StreamingResponse(
        response.aiter_raw(),
        status_code=response.status_code,
        headers=response_headers,
        media_type=response.headers.get("Content-Type"),
    )
