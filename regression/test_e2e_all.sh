#!/usr/bin/env bash
# Run all maintained E2E shell suites and store logs/statistics per suite.

set -euo pipefail

CONFIG_FILE="${GANTRY_SERVER__CONFIG_FILE:-gantry.toml}"
RESULTS_BASE="${RESULTS_BASE:-test-results/e2e}"
RUN_ID="${RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
RESULT_DIR="$RESULTS_BASE/$RUN_ID"
SERVER_LOG="$RESULT_DIR/gantry-server.log"
SUMMARY_TSV="$RESULT_DIR/summary.tsv"
SUMMARY_MD="$RESULT_DIR/summary.md"
TIMEOUT_SECONDS="${E2E_SUITE_TIMEOUT_SECONDS:-240}"
START_GANTRY_SERVER="${START_GANTRY_SERVER:-auto}"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
API_HEALTH_URL="${API_HEALTH_URL:-http://localhost:8000/management/v1/organizations/permissions}"
KC_HEALTH_URL="${KC_HEALTH_URL:-$KEYCLOAK_URL/realms/${REALM:-gantry}/.well-known/openid-configuration}"

GANTRY_SERVER_PID=""

mkdir -p "$RESULT_DIR"
ln -sfn "$RUN_ID" "$RESULTS_BASE/latest"
printf 'suite\tstatus\tpass\tfail\ttotal\tduration_seconds\tlog\traw_log\n' > "$SUMMARY_TSV"
cat > "$SUMMARY_MD" <<MD
# E2E Shell Test Results

- Run ID: $RUN_ID
- Config: $CONFIG_FILE
- Started at: $(date -Is)

| Suite | Status | Passed | Failed | Total | Duration | Log | Raw Log |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
MD

strip_ansi() {
  sed -r 's/\x1B\[[0-9;]*[mK]//g'
}

http_code() {
  local url="$1"
  curl --connect-timeout 3 --max-time 8 -s -o /dev/null -w '%{http_code}' "$url" || true
}

wait_for_http_200() {
  local name="$1"
  local url="$2"
  local attempts="${3:-60}"
  local code
  for _ in $(seq 1 "$attempts"); do
    code=$(http_code "$url")
    if [ "$code" = "200" ]; then
      return 0
    fi
    sleep 2
  done
  echo "Timed out waiting for $name at $url" >&2
  return 1
}

start_gantry_if_needed() {
  local api_code
  api_code=$(http_code "$API_HEALTH_URL")
  if [ "$api_code" = "200" ]; then
    echo "API server already reachable at $API_HEALTH_URL"
    return 0
  fi

  if [ "$START_GANTRY_SERVER" = "0" ] || [ "$START_GANTRY_SERVER" = "false" ]; then
    echo "API server is not reachable and START_GANTRY_SERVER=$START_GANTRY_SERVER" >&2
    return 1
  fi

  echo "API server not reachable. Running migrations and starting Gantry server..."
  GANTRY_SERVER__CONFIG_FILE="$CONFIG_FILE" PYTHONPATH=src uv run gantry server -f "$CONFIG_FILE" migrate >> "$SERVER_LOG" 2>&1
  GANTRY_SERVER__CONFIG_FILE="$CONFIG_FILE" PYTHONPATH=src uv run gantry server -f "$CONFIG_FILE" >> "$SERVER_LOG" 2>&1 &
  GANTRY_SERVER_PID=$!
  echo "$GANTRY_SERVER_PID" > "$RESULT_DIR/gantry-server.pid"
  wait_for_http_200 "Gantry API" "$API_HEALTH_URL" 90
}

cleanup() {
  if [ -n "${GANTRY_SERVER_PID:-}" ]; then
    if kill -0 "$GANTRY_SERVER_PID" >/dev/null 2>&1; then
      echo "Stopping Gantry server pid=$GANTRY_SERVER_PID"
      kill "$GANTRY_SERVER_PID" >/dev/null 2>&1 || true
      wait "$GANTRY_SERVER_PID" >/dev/null 2>&1 || true
    fi
  fi
}
trap cleanup EXIT

extract_counts() {
  local log_file="$1"
  local line pass fail total
  line=$(grep -E 'Results: [0-9]+ passed, [0-9]+ failed' "$log_file" | tail -n1 || true)
  if [ -n "$line" ]; then
    pass=$(echo "$line" | sed -E 's/.*Results: ([0-9]+) passed, ([0-9]+) failed.*/\1/')
    fail=$(echo "$line" | sed -E 's/.*Results: ([0-9]+) passed, ([0-9]+) failed.*/\2/')
    total=$(echo "$line" | sed -E 's/.*out of ([0-9]+).*/\1/')
    if [ "$total" = "$line" ]; then
      total=$((pass + fail))
    fi
  else
    pass=""
    fail=""
    total=""
  fi
  printf '%s\t%s\t%s' "$pass" "$fail" "$total"
}

run_suite() {
  local suite="$1"
  local script="$2"
  local suite_dir="$RESULT_DIR/$suite"
  local log_file="$suite_dir/console.log"
  local raw_log_file="$suite_dir/console.raw.log"
  local start end duration status exit_code counts pass fail total

  mkdir -p "$suite_dir"
  echo "========== Running $suite ($script) ==========" | tee "$raw_log_file"
  start=$(date +%s)
  set +e
  timeout "$TIMEOUT_SECONDS" bash "$script" >> "$raw_log_file" 2>&1
  exit_code=$?
  set -e
  end=$(date +%s)
  duration=$((end - start))

  strip_ansi < "$raw_log_file" > "$log_file"

  if [ "$exit_code" -eq 0 ]; then
    status="PASS"
  elif [ "$exit_code" -eq 124 ]; then
    status="TIMEOUT"
  else
    status="FAIL"
  fi

  counts=$(extract_counts "$log_file")
  pass=$(echo "$counts" | cut -f1)
  fail=$(echo "$counts" | cut -f2)
  total=$(echo "$counts" | cut -f3)

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$suite" "$status" "$pass" "$fail" "$total" "$duration" "$log_file" "$raw_log_file" >> "$SUMMARY_TSV"
  printf '| `%s` | %s | %s | %s | %s | %ss | `%s` | `%s` |\n' "$suite" "$status" "${pass:-}" "${fail:-}" "${total:-}" "$duration" "$log_file" "$raw_log_file" >> "$SUMMARY_MD"
  {
    printf 'SUITE=%q\n' "$suite"
    printf 'SCRIPT=%q\n' "$script"
    printf 'STATUS=%q\n' "$status"
    printf 'PASS_COUNT=%q\n' "${pass:-}"
    printf 'FAIL_COUNT=%q\n' "${fail:-}"
    printf 'TOTAL_COUNT=%q\n' "${total:-}"
    printf 'DURATION_SECONDS=%q\n' "$duration"
    printf 'LOG_FILE=%q\n' "$log_file"
    printf 'RAW_LOG_FILE=%q\n' "$raw_log_file"
  } > "$suite_dir/summary.env"

  echo "[$status] $suite (${duration}s) -> $log_file"
  if [ "$status" != "PASS" ]; then
    return 1
  fi
  return 0
}

preflight() {
  local kc_code
  kc_code=$(http_code "$KC_HEALTH_URL")
  if [ "$kc_code" != "200" ]; then
    echo "Keycloak is not reachable at $KC_HEALTH_URL (HTTP $kc_code)" >&2
    return 1
  fi
  start_gantry_if_needed
}

SUITES=(
  "permissions_catalog:regression/test_permissions_api.sh"
  "organization:regression/test_organization_api.sh"
  "project:regression/test_project_api.sh"
  "org_project:regression/test_org_project_api.sh"
  "settings_limits:regression/test_settings_limits_api.sh"
  "api_key:regression/test_api_key_api.sh"
  "frontend_auth_org_project:regression/test_frontend_auth_org_project.sh"
  "admin:regression/test_admin_api.sh"
  "admin_dashboard:regression/test_admin_dashboard_api.sh"
  "admin_alias_paths:regression/test_admin_alias_paths.sh"
)

preflight

overall=0
for entry in "${SUITES[@]}"; do
  suite="${entry%%:*}"
  script="${entry#*:}"
  if [ ! -x "$script" ]; then
    echo "Script is missing or not executable: $script" >&2
    overall=1
    continue
  fi
  if ! run_suite "$suite" "$script"; then
    overall=1
  fi
  echo ""
done

{
  echo ""
  echo "Finished at: $(date -Is)"
  echo "Overall: $([ "$overall" -eq 0 ] && echo PASS || echo FAIL)"
} >> "$SUMMARY_MD"

cat "$SUMMARY_MD"
exit "$overall"
