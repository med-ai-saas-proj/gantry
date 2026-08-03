from gantry.settings import AppStage, getAppSettings
from gantry.management.api_key import (
    ApiKeyInfo,
    ApiKeyService,
    ApiKeyHeaderNotFound,
    api_key_header,
    getApiKeyService,
)
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
from contextlib import asynccontextmanager
from urllib.parse import urljoin

import httpx
from fastapi import Path, Depends, FastAPI, Request, Security, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware


client = httpx.AsyncClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await client.aclose()


gateway_app = FastAPI(
    debug=getAppSettings().stage == AppStage.DEV, lifespan=lifespan
)


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
    api_key: Annotated[str, Security(api_key_header)],
    api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
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
        api_key,
        full_path,
        gateway_service,
        transaction_service,
        api_key_service,
        background_tasks,
    )


@gateway_app.api_route(
    "/{route_name}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def gateway_proxy(
    route_name: Annotated[str, Path()],
    request: Request,
    api_key: Annotated[str, Security(api_key_header)],
    api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
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
        api_key,
        None,
        gateway_service,
        transaction_service,
        api_key_service,
        background_tasks,
    )


async def _gateway_proxy(
    route_name: str,
    request: Request,
    api_key: str | None,
    full_path: Optional[str],
    gateway_service: ApiGatewayService,
    transaction_service: TransactionService,
    api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    background_tasks: BackgroundTasks,
):
    destination = gateway_service.getDestination(route_name=route_name).unwrap()
    if destination.require_key:
        if api_key is None:
            raise ApiKeyHeaderNotFound()
        user_info = await api_key_service.parseApiKey(api_key)
        apikey_info = user_info.unwrap()
        (await api_key_service.rateLimit(apikey_info)).unwrap()
        gateway_service.checkPermission(
            apikey_info["permissions"], destination
        ).unwrap()
    else:
        apikey_info = None

    key = uuid7()
    transaction_uuid = None
    if destination.auto_charge is not None and apikey_info is not None:
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
    if apikey_info is not None:
        incoming_headers.update(_inject_api_key_context_headers(apikey_info))

    request_timeout = getApiGatewaySettings().request_timeout.total_seconds()

    full_url = urljoin(
        destination.address.encoded_string(),
        full_path,
    )
    req = client.build_request(
        method=request.method,
        url=full_url,
        headers=incoming_headers,
        content=request.stream(),
        params=request.query_params,
        timeout=request_timeout,
    )
    response = await client.send(request=req, stream=True)
    response_headers = filter_headers(dict(response.headers))

    if apikey_info is not None:
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
    return StreamingResponse(
        response.aiter_raw(),
        status_code=response.status_code,
        headers=response_headers,
        media_type=response.headers.get("Content-Type"),
    )
