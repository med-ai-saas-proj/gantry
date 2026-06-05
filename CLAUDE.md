# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gantry is a multi-tenant SaaS backend built with FastAPI (Python 3.13+). It provides organization/project management, billing (Stripe), API key management, AI conversation services, file storage (S3), and an API gateway — all behind Keycloak authentication. Uses `uv` as package manager with a workspace setup (the main app + `packages/pyrusult`).

## Common Commands

**Install dependencies:** `uv sync --dev --frozen`

**Run dev server:** `uv run gantry server -f gantry.toml` (requires `gantry.toml` from copying `example.gantry.toml`)

**Start backing services:** `docker compose up` (TimescaleDB, pgvector, Redis, Keycloak, Mailpit, OpenTelemetry collector, Loki)

**Run DB migrations:** `uv run gantry server -f gantry.toml migrate`

**Run alembic directly:** `GANTRY_SERVER__CONFIG_FILE=example.gantry.toml uv run alembic`

**Format & lint:** `./scripts/tidy.sh` (runs `ruff check --fix --select I` then `ruff format`)

**Type check:** `uv run pyrefly check`

**Reset database:** `scripts/reset-db.sh` (then re-migrate and recreate test account)

## Architecture

### Two FastAPI Sub-Applications Mounted on a Root App

The server runs two uvicorn instances concurrently:
- **Main app** (public, default port 8000): mounts `/management` and `/service` sub-apps, each is a full `FastAPI()` instance with its own OpenAPI docs at `/docs` (DEV only, uses Scalar).
- **Internal app** (port 9000): billing webhooks, Prometheus metrics.

### Management vs Service Split

- **`management/`** — tenant/admin APIs: organizations, projects, billing, API keys, auth, user logging. Routes are under `/management/v1/`.
- **`service/`** — end-user product APIs: conversations (AI agents), file storage. Routes under `/service/v1/`. Authenticated via API keys rather than Keycloak tokens.
- **`api_gateway/`** — reverse-proxy gateway that routes external API calls through configured endpoints with permission checks and rate limiting.

### Module Structure (Vertical Slices)

Each feature module (e.g., `management/organization/`, `service/utils/conversation/`) follows this pattern:
- `models.py` — SQLAlchemy ORM models (extend `BaseSQLModel` or `BaseTimescaleSQLModel`)
- `entities.py` — domain/business entities
- `dtos.py` — Pydantic request/response schemas
- `repositories.py` — data access, extends generic `Repository[TEntity, TKey]` base class
- `services.py` — business logic
- `routes.py` / `routers.py` — FastAPI route definitions
- `dependencies.py` — FastAPI dependency injection
- `factories.py` — singleton construction via `@lru_cache(1)` (wires services, repos, clients)
- `settings.py` — module-specific config (subsection of `AppSettings`)
- `permissions.py` — permission definitions for the module
- `*_test.py` — tests (Python `unittest`) live alongside source files, not in a separate directory

### Configuration System

Settings are loaded via `pydantic-settings` with this priority: CLI args > env vars (prefix `GANTRY_`, nested with `__`) > TOML config file (`-f` flag) > `.env` file. The `AppSettings` class is a singleton accessed via `getAppSettings()`. Each module has its own settings subsection (e.g., `[db]`, `[auth]`, `[billing]` in TOML).

### Database

- **TimescaleDB** (PostgreSQL + timescale extension) on port 5432 — primary data store
- **pgvector** (PostgreSQL + vector extension) on port 5433 — vector embeddings
- **Redis** — caching, rate limiting
- Async SQLAlchemy with `asyncpg` driver. Sessions managed by `AsyncSessionManager`; callers must commit manually (because the Result pattern can't trigger rollback on `return Error(...)`).
- Two base classes: `BaseSQLModel` (regular tables) and `BaseTimescaleSQLModel` (timescale hypertables). Don't share tables between modules.
- Alembic for migrations with async support. The `alembic/env.py` imports `main_app` to discover all models.

### Error Handling

Uses a Result pattern (via `pyrusult` workspace package, a Rust `Result<T, E>` port). Errors are class-based: `RecoverableError` (4xx, subclass with `status`, `title`, `code` ClassVars) and `UnrecoverableError` (5xx). Global exception handlers convert these to RFC 7807 `ProblemDetails` responses.

### Auth

Keycloak for user authentication (OIDC/JWT). Organization memberships and permissions are stored as Keycloak user attributes and included in JWT claims. A service account client (`gantry-backend`) is used for admin operations. API keys provide a separate auth path for `service/` endpoints.

### Observability

Full OpenTelemetry instrumentation (traces, metrics, logs) exported via OTLP. FastAPI, SQLAlchemy, asyncpg, Redis, and httpx are all instrumented. Prometheus metrics optionally exposed on the internal app. Loki for log aggregation, Jaeger for traces, Grafana dashboards.

## Code Style

- Line length: 80 characters
- Ruff for linting and formatting (Google-style docstrings, isort with first-party imports prioritized)
- Imports are sorted with `src` and `.` as first-party; standard-library and third-party come after
- Pre-commit hook runs `./scripts/tidy.sh` — always run this before committing
