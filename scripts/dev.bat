uv run alembic upgrade head --env-file .env
uv run uvicorn src.main.app:main_app --host 0.0.0.0 --port 8000 --env-file .env --reload
