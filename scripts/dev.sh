uv run uvicorn server:app --host 0.0.0.0 --port 8000 \
    --env-file .env \
    --log-config log-config.json \
    --reload