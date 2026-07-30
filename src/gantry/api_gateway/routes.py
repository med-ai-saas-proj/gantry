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
import asyncio
from uuid import UUID
from typing import Optional, Annotated
from urllib.parse import urljoin

import httpx
from fastapi import Path, Depends, FastAPI, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware


gateway_app = FastAPI(debug=getAppSettings().stage == AppStage.DEV)

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

GATEWAY_INJECTED_HEADERS = {
    "x-organization-uuid",
    "x-project-uuid",
    "x-api-key-uuid",
    "x-permissions",
    "x-rpm-limit-organization",
    "x-rpm-limit-project",
    "x-spending-limit-organization",
    "x-spending-limit-project",
    "x-forwarded-for",
    "x-forwarded-proto",
    "x-forwarded-host",
}

STRIPPED_HEADERS = HOP_BY_HOP_HEADERS | GATEWAY_INJECTED_HEADERS


def filter_headers(headers: dict[str, str]) -> dict[str, str]:
    """Remove hop-by-hop and gateway-injected headers."""
    return {
        k: v for k, v in headers.items() if k.lower() not in STRIPPED_HEADERS
    }


def _build_forwarded_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {}
    client_host = request.client.host if request.client else None

    existing_xff = request.headers.get("x-forwarded-for")
    if client_host:
        headers["X-Forwarded-For"] = (
            f"{existing_xff}, {client_host}" if existing_xff else client_host
        )
    elif existing_xff:
        headers["X-Forwarded-For"] = existing_xff

    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    headers["X-Forwarded-Proto"] = proto

    host = request.headers.get("x-forwarded-host") or request.headers.get(
        "host", ""
    )
    if host:
        headers["X-Forwarded-Host"] = host

    return headers


def _inject_api_key_context_headers(
    api_key_info: ApiKeyInfo,
) -> dict[str, str]:
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
    incoming_headers.update(_build_forwarded_headers(request))
    incoming_headers.update(_inject_api_key_context_headers(apikey_info))

    request_timeout = getApiGatewaySettings().request_timeout.total_seconds()
    client = httpx.AsyncClient(timeout=request_timeout, follow_redirects=False)

    full_url = urljoin(
        destination.address.encoded_string(),
        full_path,
    ).rstrip("/")
    req = client.build_request(
        method=request.method,
        url=full_url,
        headers=incoming_headers,
        content=request.stream(),
        params=request.query_params,
    )
    response = await client.send(request=req, stream=True)
    response_headers = filter_headers(dict(response.headers))

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
