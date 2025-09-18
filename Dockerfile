FROM ghcr.io/astral-sh/uv:latest

WORKDIR /app
COPY pyproject.yaml uv.lock /app/
RUN uv sync --frozen
COPY . .
ENTRYPOINT [ "/app/scripts/dev.sh" ]
