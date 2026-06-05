FROM ghcr.io/astral-sh/uv:alpine3.23

WORKDIR /app

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

EXPOSE 8000

ENTRYPOINT [ "uv", "run", "gantry" ]
CMD [ "server", "--config-file", "gantry.toml" ]
