"""Shared lightweight runtime health endpoints."""

from typing import Literal
from typing import TypedDict
from fastapi import FastAPI
from fastapi.responses import JSONResponse

class HealthResponse(TypedDict):
    status: Literal["OK"]

async def health_response() -> HealthResponse:
    return JSONResponse(HealthResponse(status="OK"))


def setup_health_routes(app: FastAPI) -> None:
    app.add_api_route(
        "/health",
        health_response,
        methods=["GET"],
        include_in_schema=False,
    )
    app.add_api_route(
        "/ready",
        health_response,
        methods=["GET"],
        include_in_schema=False,
    )
