# How to setup local development environment

## Prerequisites

- uv: https://docs.astral.sh/uv/
- Docker, Docker compose or Podman

## Install dependencies

1. Create a virtual environment in the current directory, install python and dependencies `uv sync --dev --all-extras --frozen`
1. Setup crawl4ai `uv run crawl4ai-setup`

## .env files

Go ask other people for it. We currently doesn't have any good ways to share them.

## Run

1. Start other services (postgres, redis, ...) `docker compose -f compose.dev.yaml up`
1. Start the server `./scripts/dev.sh`

## Debugging

Start the debugger at [server.py](/server.py)

### VScode

1. Open [server.py](/server.py)
1. Start debugger (F5)

## Testing

This project used Python's unittest

## Generate scaffold for new app

The new_module script is used to generate app's scaffold. It generate new files using templates in template/new_module directory