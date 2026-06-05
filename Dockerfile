FROM python:3.13

COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /uvx /bin/

WORKDIR /app

COPY . .
RUN uv sync --frozen

EXPOSE 8000

ENTRYPOINT [ "uv", "run", "gantry" ]
CMD [ "server", "--config-file", "example.gantry.toml" ]
