from gantry.settings import AppStage, getAppSettings
from gantry.management.api_key import ApiKeyInfo, getApiKeyInfo
from gantry.shared.health import setup_health_routes

from .service import ApiGatewayService
from .settings import getApiGatewaySettings
from .factories import getApiGatewayService

import json
from typing import Annotated
from urllib.parse import urljoin

import httpx
from fastapi import Path, Depends, FastAPI, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask


gateway_app = FastAPI(debug=getAppSettings().stage == AppStage.DEV)

setup_health_routes(gateway_app)

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


def filter_headers(headers: dict[str, str]) -> dict[str, str]:
    """Remove hop-by-hop headers + auto-calculated ones."""
    return {
        k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS
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
    "/{route_name}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@gateway_app.api_route(
    "/{route_name}/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def gateway_proxy(
    route_name: Annotated[str, Path()],
    full_path: Annotated[str | None, Path()],
    request: Request,
    apikey_info: Annotated[ApiKeyInfo, Depends(getApiKeyInfo)],
    gateway_service: Annotated[
        ApiGatewayService, Depends(getApiGatewayService)
    ],
):
    destination = gateway_service.getDestination(route_name=route_name).unwrap()
    gateway_service.checkPermission(
        apikey_info["permissions"], destination
    ).unwrap()

    incoming_headers = filter_headers(dict(request.headers))
    incoming_headers.update(_inject_api_key_context_headers(apikey_info))

    request_timeout = getApiGatewaySettings().request_timeout.total_seconds()
    client = httpx.AsyncClient(timeout=request_timeout)

    full_url = urljoin(destination.address, full_path)
    req = client.build_request(
        method=request.method,
        url=full_url,
        headers=incoming_headers,
        content=request.stream(),
        params=request.query_params,
    )
    response = await client.send(request=req, stream=True)
    response_headers = filter_headers(dict(response.headers))

    return StreamingResponse(
        response.aiter_raw(),
        status_code=response.status_code,
        headers=response_headers,
        media_type=response.headers.get("Content-Type"),
        background=BackgroundTask(client.aclose),
    )
