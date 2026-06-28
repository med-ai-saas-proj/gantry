from gantry.settings import AppStage, getAppSettings
from gantry.shared.health import setup_health_routes
from gantry.shared.custom_types.error_exception import RecoverableError

from .settings import getApiGatewaySettings

from typing import Annotated

import httpx
from fastapi import Path, FastAPI, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware


docs_app = FastAPI(debug=getAppSettings().stage == AppStage.DEV)

setup_health_routes(docs_app)

docs_app.add_middleware(
    CORSMiddleware,
    allow_origins=getAppSettings().allowed_origins,
    allow_credentials=True,  # keep only if you really need cookies/auth
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@docs_app.get("/available", status_code=200)
async def getDocs() -> list[str]:
    return [
        route
        for route, route_config in getApiGatewaySettings().routes.items()
        if route_config.openapi_json_url
    ]


class DocNotFound(RecoverableError):
    code = "doc-not-found"
    status = 404
    title = "Document for this service does not exist."
    delail = "Document for this service does not exist."


@docs_app.get(
    "/{app_name}/openapi.json",
)
async def getAppDoc(
    request: Request,
    app_name: Annotated[str, Path()],
    background_tasks: BackgroundTasks,
):
    routes = getApiGatewaySettings().routes

    if app_name not in routes:
        raise DocNotFound()
    route = routes[app_name]
    if route.openapi_json_url is None:
        raise DocNotFound()

    request_timeout = getApiGatewaySettings().request_timeout.total_seconds()
    client = httpx.AsyncClient(timeout=request_timeout)
    req = client.build_request(
        method="GET",
        url=route.openapi_json_url.encoded_string(),
        headers=request.headers,
        content=request.stream(),
        params=request.query_params,
    )
    response = await client.send(request=req, stream=True)

    background_tasks.add_task(client.aclose)
    return StreamingResponse(
        response.aiter_raw(),
        status_code=response.status_code,
        headers=response.headers,
        media_type=response.headers.get("Content-Type"),
    )
