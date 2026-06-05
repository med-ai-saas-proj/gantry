#! /bin/bash
set -ex
export UV_ENV_FILE=.env
uv sync --frozen --all-extras
uv run crawl4ai-setup
