# Gantry Test Suites

The `tests/` folder is organized by Gantry behavior and user-story responsibility. Source-adjacent unit tests remain under `src/**/**/*_test.py` and `packages/**/test.py`.

## Suite Taxonomy

| Suite | Path | Stack | Purpose | CI policy |
| --- | --- | --- | --- | --- |
| Unit | `src/**/**/*_test.py`, `packages/**/test.py` | `pytest`, mocks/fakes | Service/repository/factory/permission logic | PR into `dev` |
| API contract | `tests/api/` | `pytest`, `httpx.AsyncClient`, ASGI transport, dependency overrides, `respx` | Management HTTP contracts and route interactions without real services | PR into `dev` |
| Integration | `tests/integration/` | Testcontainers, real storage/cache/identity/email providers | Real Gantry stories: identity, invitation delivery, persistence/cache | workflow_dispatch, push/PR into `main` for infra/storage/identity/integration changes |
| Regression | `tests/regression/` | `pytest-snapshot`, `deepdiff`, `schemathesis` | Stable public contracts and compatibility | PR into `dev` |
| Performance | `tests/performance/` | `pytest-benchmark`, `locust`, `k6` | Hot-path benchmarks and load smoke entrypoints | manual/nightly |
| E2E | `tests/e2e/` | Playwright `APIRequestContext`, Docker Compose | Backend-first full stack journeys | manual/nightly |
| Automation | `tests/automation/` | `pytest-cov`, `allure-pytest` | Deploy smoke and report artifacts | manual/nightly |

## Commands

```bash
GANTRY_SERVER__CONFIG_FILE=gantry.toml PYTHONPATH=src make test-unit
GANTRY_SERVER__CONFIG_FILE=gantry.toml PYTHONPATH=src make test-api
GANTRY_SERVER__CONFIG_FILE=gantry.toml PYTHONPATH=src uv run --group dev pytest tests/integration -m integration -q
GANTRY_SERVER__CONFIG_FILE=gantry.toml PYTHONPATH=src make test-regression
GANTRY_SERVER__CONFIG_FILE=gantry.toml PYTHONPATH=src make test-perf
GANTRY_SERVER__CONFIG_FILE=example.gantry.toml PYTHONPATH=src make test-e2e-backend
GANTRY_SERVER__CONFIG_FILE=gantry.toml PYTHONPATH=src make test-automation
GANTRY_SERVER__CONFIG_FILE=gantry.toml PYTHONPATH=src make test-ci-fast
GANTRY_SERVER__CONFIG_FILE=gantry.toml PYTHONPATH=src make test-ci-full
```

## Coverage Strategy

- Coverage is risk-based, not brute-force full matrix.
- Unit tests own domain edge cases: not found, conflict, invalid permission, unauthorized actor, archived project, missing org/project context.
- API tests own route-layer HTTP contracts: OpenAPI presence, all-route missing-auth sweep, status codes, validation `422`, pagination forwarding, response shape, admin aliases, and cross-module orchestration.
- `make test-api` enforces `COVERAGE_FAIL_UNDER=80` against route/app entry modules via `tests/api/coverage.ini`; domain service coverage remains owned by unit tests.
- Integration tests own Gantry user stories backed by Testcontainers: management identity token/profile/admin role, invitation email delivery, migration/schema contracts, cache hit/miss/delete behavior, API-key auth, and billing usage/cache flows.
- Regression tests own public compatibility: path snapshots, operation contract snapshots, selected response schemas, permission catalogs, hidden aliases, removed ambiguous ID paths.
- E2E uses backend-first full-stack HTTP journeys through Playwright APIRequestContext.
- Performance/E2E are intentionally separated from PR gates to reduce flake and runtime.

## Naming Rules

- Test modules should describe Gantry behavior or a user story, not the underlying dependency name.
- Dependency names may still appear in settings, Docker service names, or fixture internals where they are the actual integration provider.
- Do not add unrelated sample domains unless they are part of Gantry behavior.

## Artifacts

- `reports/bench.json`: pytest-benchmark output from `make test-perf`.
- `reports/api/`: API JUnit and route-layer coverage XML from `make test-api`.
- `reports/regression/`: regression JUnit XML from `make test-regression`.
- `reports/automation/`: automation JUnit and coverage XML from `make test-automation`.
- `reports/allure/`: Allure result files from `make test-automation`.
- `reports/e2e/`: backend E2E JUnit XML, compose logs, and Mailpit dumps.
- `fixtures/keycloak-realm.json`: committed realm import used by Docker/test environments.
