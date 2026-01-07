#! /bin/bash
uv run --no-sync alembic upgrade head
uv run uvicorn src.main.app:main_app --host 0.0.0.0 --port 8000
