#! /bin/bash
export UV_ENV_FILE=.env
uv run --no-sync alembic upgrade head
uv run --no-sync uvicorn server:app --host 0.0.0.0 --port 8000 \
    --log-config log-config.json