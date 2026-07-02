# syntax=docker/dockerfile:1.7

FROM debian:stable-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /uvx /bin/

WORKDIR /app

COPY . .

RUN uv sync --dev --frozen

EXPOSE 8000

ENTRYPOINT ["uv", "run", "-m", "gantry"]
