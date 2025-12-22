#! /bin/bash
set -ex
export UV_ENV_FILE=.env
uv run alembic upgrade head
uv run uvicorn src.main.app:main_app --host 0.0.0.0 --port 8000 \
    --env-file .env \
    --reload
