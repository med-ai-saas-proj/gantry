#! /bin/bash
uv run ruff check --fix --select I -q "$@"
uv run ruff format -q "$@"