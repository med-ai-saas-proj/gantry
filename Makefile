.PHONY: test-unit test-api test-integration test-regression test-perf test-load-locust test-load-k6 test-e2e test-e2e-backend test-automation test-ci-fast test-ci-full test-all

GANTRY_SERVER__CONFIG_FILE ?= gantry.toml
PYTHONPATH ?= src
PYTEST ?= uv run --group dev pytest
COVERAGE_FAIL_UNDER ?= 80
AUTOMATION_COVERAGE_FAIL_UNDER ?= 0
PYTEST_XDIST ?=
API_COV_TARGETS ?= --cov=src/gantry --cov-config=tests/api/coverage.ini

export GANTRY_SERVER__CONFIG_FILE
export PYTHONPATH

test-unit:
	mkdir -p reports/unit
	./tests/unit/test_unit_all.sh --junitxml=reports/unit/junit.xml

test-api:
	mkdir -p reports/api
	$(PYTEST) tests/api -m api $(PYTEST_XDIST) $(API_COV_TARGETS) --cov-report=term-missing --cov-report=xml:reports/api/coverage.xml --junitxml=reports/api/junit.xml --cov-fail-under=$(COVERAGE_FAIL_UNDER)

test-integration:
	mkdir -p reports/integration
	$(PYTEST) tests/integration -m integration --junitxml=reports/integration/junit.xml

test-regression:
	mkdir -p reports/regression
	$(PYTEST) tests/regression -m regression --junitxml=reports/regression/junit.xml

test-perf:
	mkdir -p reports
	$(PYTEST) tests/performance -m performance --benchmark-json=reports/bench.json

test-load-locust:
	mkdir -p reports
	locust -f tests/performance/locustfile.py --headless -u $${LOCUST_USERS:-5} -r $${LOCUST_SPAWN_RATE:-1} -t $${LOCUST_RUN_TIME:-30s} --host $${BASE_URL:-http://localhost:8000} --csv reports/locust

test-load-k6:
	mkdir -p reports
	command -v k6 >/dev/null || (echo "k6 binary is required for test-load-k6" && exit 127)
	BASE_URL=$${BASE_URL:-http://localhost:8000} k6 run --summary-export reports/k6-summary.json tests/performance/k6/load_test.js

test-e2e: test-e2e-backend

test-e2e-backend:
	mkdir -p reports/e2e
	$(PYTEST) tests/e2e -m "e2e and backend_e2e" --junitxml=reports/e2e/backend-e2e.xml

test-automation:
	mkdir -p reports/allure
	mkdir -p reports/automation
	$(PYTEST) tests/automation -m "automation or smoke" --cov=gantry --cov-report=xml:reports/automation/coverage.xml --junitxml=reports/automation/junit.xml --cov-fail-under=$(AUTOMATION_COVERAGE_FAIL_UNDER) --alluredir=reports/allure

test-ci-fast: test-automation test-unit test-api test-regression

test-ci-full: test-ci-fast test-integration

test-all: test-ci-fast
