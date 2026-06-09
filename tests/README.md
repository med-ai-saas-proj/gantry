# Gantry Test Suites

The `tests/` folder is organized by Gantry behavior and user-story responsibility. Source-adjacent unit tests remain under `src/**/**/*_test.py` and `packages/**/test.py`.

## Suite Taxonomy

| Suite | Path | Stack | Purpose | CI policy |
| --- | --- | --- | --- | --- |
| Unit | `src/**/**/*_test.py`, `packages/**/test.py` | `pytest`, mocks/fakes | Service/repository/factory/permission logic | PR into `dev` |
| API contract | `tests/api/` | `pytest`, `httpx.AsyncClient`, ASGI transport, dependency overrides, `respx` | Management HTTP contracts and route interactions without real services | PR into `dev` |
| Integration | `tests/integration/` | Testcontainers, real storage/cache/identity/email providers | Real Gantry stories: identity, invitation delivery, persistence/cache | workflow_dispatch, push/PR into `main` for infra/storage/identity/integration changes |
| Regression | `tests/regression/` | `deepdiff`, `schemathesis` | Backward compatibility and unexpected `5xx` fuzz checks | PR into `dev` |
| Performance | `tests/performance/` | `pytest-benchmark`, `locust`, `k6` | Hot-path benchmarks and load smoke entrypoints | manual/nightly |
| E2E | `tests/e2e/` | Playwright `APIRequestContext`, Docker Compose | Backend-first full stack journeys | manual/nightly |
| Automation | `tests/automation/` | `pytest-cov`, `allure-pytest` | Deploy smoke and report artifacts | manual/nightly |

## Commands

Install dependencies once:

```bash
uv sync --group dev
```

Use `example.gantry.toml` for fast local contract/regression tests that do not
need real secrets. Use `gantry.toml` when a suite needs your local stack config.

```bash
GANTRY_SERVER__CONFIG_FILE=example.gantry.toml PYTHONPATH=src make test-unit
GANTRY_SERVER__CONFIG_FILE=example.gantry.toml PYTHONPATH=src make test-api
GANTRY_SERVER__CONFIG_FILE=example.gantry.toml PYTHONPATH=src make test-regression
GANTRY_SERVER__CONFIG_FILE=example.gantry.toml PYTHONPATH=src make test-perf
GANTRY_SERVER__CONFIG_FILE=example.gantry.toml PYTHONPATH=src make test-automation
GANTRY_SERVER__CONFIG_FILE=example.gantry.toml PYTHONPATH=src make test-ci-fast
```

Suites that use real services:

```bash
GANTRY_SERVER__CONFIG_FILE=example.gantry.toml PYTHONPATH=src make test-integration
GANTRY_SERVER__CONFIG_FILE=example.gantry.toml PYTHONPATH=src make test-e2e-backend
GANTRY_SERVER__CONFIG_FILE=example.gantry.toml PYTHONPATH=src make test-ci-full
```

Optional load tests require a running server:

```bash
BASE_URL=http://localhost:8000 make test-load-k6
BASE_URL=http://localhost:8000 make test-load-locust
```

## Local CI With `act`

Use `act` to run GitHub Actions workflows against the current working tree.
This is useful before pushing workflow or test changes.

```bash
act workflow_dispatch \
  -W .github/workflows/regression-test.yml \
  -j regression \
  --container-architecture linux/amd64 \
  -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

Common workflow jobs:

```bash
act workflow_dispatch -W .github/workflows/unit-test.yml -j unit --container-architecture linux/amd64 -P ubuntu-latest=catthehacker/ubuntu:act-latest
act workflow_dispatch -W .github/workflows/api-test.yml -j api --container-architecture linux/amd64 -P ubuntu-latest=catthehacker/ubuntu:act-latest
act workflow_dispatch -W .github/workflows/automation-test.yml -j smoke --container-architecture linux/amd64 -P ubuntu-latest=catthehacker/ubuntu:act-latest
act workflow_dispatch -W .github/workflows/regression-test.yml -j regression --container-architecture linux/amd64 -P ubuntu-latest=catthehacker/ubuntu:act-latest
act workflow_dispatch -W .github/workflows/integration-test.yml -j integration --container-architecture linux/amd64 -P ubuntu-latest=catthehacker/ubuntu:act-latest
act workflow_dispatch -W .github/workflows/e2e-test.yml -j e2e --container-architecture linux/amd64 -P ubuntu-latest=catthehacker/ubuntu:act-latest
act workflow_dispatch -W .github/workflows/performance-test.yml -j benchmark --container-architecture linux/amd64 -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

Notes:

- `act` runs with the files currently in your workspace, including uncommitted
  changes.
- Integration and E2E workflows need Docker socket access and can start
  containers.
- If `act` emits Docker Hub credential warnings or Node deprecation warnings
  but the job passes, they are not Gantry test failures.

## Coverage Strategy

- Coverage is risk-based, not brute-force full matrix.
- Unit tests own domain edge cases: not found, conflict, invalid permission, unauthorized actor, archived project, missing org/project context.
- API tests own route-layer HTTP contracts: exercised endpoint behavior, all-route missing-auth/no-5xx sweep, status codes, validation `422`, pagination forwarding, response shape, admin aliases, and cross-module orchestration.
- `make test-api` enforces `COVERAGE_FAIL_UNDER=80` against route/app entry modules via `tests/api/coverage.ini`; domain service coverage remains owned by unit tests.
- Integration tests own Gantry user stories backed by Testcontainers: management identity token/profile/admin role, invitation email delivery, migration/schema contracts, cache hit/miss/delete behavior, API-key auth, and billing usage/cache flows.
- Regression tests own public compatibility and resilience: removed ambiguous ID paths stay removed, selected public DTO fields stay compatible, and Schemathesis fuzzing catches unexpected `5xx`.
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
