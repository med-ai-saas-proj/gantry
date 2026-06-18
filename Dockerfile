# syntax=docker/dockerfile:1.7

FROM alpine:3.23 AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /uvx /bin/

WORKDIR /app

ENV UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/app/.python

COPY .python-version pyproject.toml uv.lock README.md ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM alpine:3.23

ARG BUILD_DATE=unknown
ARG VCS_REF=unknown

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1

LABEL org.opencontainers.image.title="gantry" \
      org.opencontainers.image.description="Gantry API service" \
      org.opencontainers.image.created="$BUILD_DATE" \
      org.opencontainers.image.revision="$VCS_REF"

RUN addgroup -S gantry \
    && adduser -S -G gantry -h /app -s /sbin/nologin gantry

WORKDIR /app

COPY --from=builder --chown=gantry:gantry /app /app

USER gantry

EXPOSE 8000

ENTRYPOINT ["/app/.venv/bin/python", "-m", "gantry"]
