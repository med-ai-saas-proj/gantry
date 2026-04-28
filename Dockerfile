FROM python:3.13

COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock /app
RUN uv sync --frozen

COPY . .

ENTRYPOINT [ "uv", "run", "gantry" ]

CMD [ "server", "--config-file", "example.gantry.toml" ]
