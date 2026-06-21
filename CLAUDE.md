# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gantry is a Python 3.13 backend service built with FastAPI, SQLAlchemy (async via asyncpg), and Keycloak for auth. It provides AI conversation, RAG, file storage, billing, organization/project management, and an API gateway. Configuration is TOML-based (`gantry.toml`), with settings layered from env vars (prefix `GANTRY_`, nested with `__`), TOML, and `.env` files.

## Commands

```bash
# Install dependencies
uv sync --group dev

# Run dev server (requires Docker services running)
docker compose --profile frontend-dev up
# Or manually: docker compose up && ./scripts/dev.sh

# Format & lint (ALWAYS run before committing)
./scripts/tidy.sh

# Run alembic migrations
GANTRY_SERVER__CONFIG_FILE=example.gantry.toml uv run alembic upgrade head

# Tests (set these env vars first)
export GANTRY_SERVER__CONFIG_FILE=example.gantry.toml
export PYTHONPATH=src

make test-unit          # Source-adjacent *_test.py files under src/
make test-api           # HTTP contract tests (80% coverage gate)
make test-regression    # Backward compat + schemathesis fuzz
make test-automation    # Deploy smoke + allure reports
make test-ci-fast       # automation + unit + API + regression
make test-integration   # Requires Docker (testcontainers)
make test-e2e-backend   # Full-stack backend journeys
make test-ci-full       # test-ci-fast + integration

# Run a single unit test file
uv run pytest src/gantry/management/project/services_test.py

# Type checking
uv run pyrefly check
```

## Architecture

The app is composed of multiple mounted FastAPI sub-applications under a single `main_app`:

- **`/service`** — User-facing features: AI conversation (sequential & tree modes), RAG (embedding + retrieval), file storage (S3-backed), AI gateway (multi-provider LLM proxy), agent orchestration
- **`/management`** — Admin/org features: auth, organization lifecycle, project management, billing (Stripe), API key management, user logging
- **`/gateway`** — API gateway that proxies requests to external services with permission checks
- **Internal app** (port 9000) — Health/ready probes, billing webhooks, metrics (Prometheus), RAG internal routes

### Module Structure

Each domain module (e.g. `management/billing/`, `service/conversation/`) follows a consistent pattern:
- `models.py` — SQLAlchemy ORM models
- `entities.py` — Domain value objects
- `dtos.py` — Pydantic request/response schemas
- `repositories.py` — Database access layer
- `services.py` — Business logic
- `routes.py` / `routers/` — FastAPI route handlers
- `factories.py` — Dependency injection factories (FastAPI `Depends`)
- `settings.py` — Module-specific config (loaded from TOML sections)
- `permissions.py` — Authorization logic
- `*_test.py` — Co-located unit tests

### Key Subsystems

- **DB**: Two SQLAlchemy bases — `BaseSQLModel` (standard tables) and `BaseTimescaleSQLModel` (TimescaleDB hypertables). Migrations via Alembic under `src/gantry/migrations/`.
- **Auth**: Keycloak OIDC + API key auth. Three Keycloak clients: `gantry-frontend`, `gantry-admin`, `gantry-backend` (service account).
- **Settings**: Pydantic Settings with CLI subcommands (`gantry server`, `gantry gen-config-schema`). Config priority: CLI > env vars > TOML > .env.
- **Observability**: OpenTelemetry (traces, metrics, logs) with OTLP export. Structured logging via `structlog`.

## Testing Conventions

- Unit tests live adjacent to source: `src/**/*_test.py`
- Integration/API/regression/e2e tests live under `tests/` with pytest markers (`@pytest.mark.api`, `@pytest.mark.integration`, etc.)
- `asyncio_mode = auto` — all async tests run automatically
- API tests use `httpx.AsyncClient` with ASGI transport and dependency overrides (no real services)
- Integration tests use `testcontainers` for real Postgres/Redis/Keycloak

## Code Style

- Formatter/linter: `ruff` (line length 80)
- Import order: first-party → local → stdlib → third-party (non-standard; enforced by ruff isort config)
- Docstrings: Google convention
- Pre-commit hook runs `./scripts/tidy.sh` on all `.py` files
- DB rule: avoid sharing tables between modules
