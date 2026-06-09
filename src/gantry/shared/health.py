"""Shared lightweight runtime health endpoints."""

from fastapi import FastAPI, Response


async def health_response() -> Response:
    return Response(status_code=200)


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
