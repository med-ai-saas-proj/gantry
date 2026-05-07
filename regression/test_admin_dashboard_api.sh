#!/usr/bin/env bash
# End-to-end smoke test for admin dashboard CRUD routes.

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000/management/v1/admin}"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-gantry}"
ADMIN_CLIENT_ID="${ADMIN_CLIENT_ID:-gantry-admin}"
KEYCLOAK_ADMIN_USERNAME="${KEYCLOAK_ADMIN_USERNAME:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
ADMIN_APP_USERNAME="${ADMIN_APP_USERNAME:-gantry-admin-user}"
ADMIN_APP_PASSWORD="${ADMIN_APP_PASSWORD:-password}"
CURL_MAX_TIME="${CURL_MAX_TIME:-30}"

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

TEST_NUM=0
PASS=0
FAIL=0
HTTP_CODE=""
RESPONSE_BODY=""
ADMIN_AUTH_TOKEN=""
ORG_ID=""
PROJECT_ID=""
API_KEY_UUID=""

run_test() {
  local description="$1"
  local expected_codes="$2"
  shift 2

  TEST_NUM=$((TEST_NUM + 1))
  echo -e "${CYAN}[TEST $TEST_NUM] $description${NC}"

  RESPONSE=$(curl --connect-timeout 5 --max-time "$CURL_MAX_TIME" -s -w "\n%{http_code}" "$@")
  HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
  RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')

  echo "  HTTP Status: $HTTP_CODE"
  echo "$RESPONSE_BODY" | jq '.' 2>/dev/null | head -30 || echo "  $RESPONSE_BODY"

  if echo "$expected_codes" | grep -qw "$HTTP_CODE"; then
    echo -e "  ${GREEN}✓ PASS (expected: $expected_codes)${NC}"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}✗ FAIL (expected: $expected_codes, got: $HTTP_CODE)${NC}"
    FAIL=$((FAIL + 1))
  fi
  echo ""
}

ensure_master_admin_token() {
  if [ -n "${MASTER_ADMIN_TOKEN:-}" ] && [ "$MASTER_ADMIN_TOKEN" != "null" ]; then
    return 0
  fi

  MASTER_ADMIN_TOKEN=$(curl -sf --connect-timeout 5 --max-time "$CURL_MAX_TIME" -X POST \
    "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=admin-cli" \
    -d "username=$KEYCLOAK_ADMIN_USERNAME" \
    -d "password=$KEYCLOAK_ADMIN_PASSWORD" \
    -d "grant_type=password" | jq -r '.access_token')

  if [ -z "${MASTER_ADMIN_TOKEN:-}" ] || [ "$MASTER_ADMIN_TOKEN" = "null" ]; then
    echo -e "${RED}✗ Failed to get Keycloak master admin token${NC}"
    exit 1
  fi
}

lookup_user_id_by_username() {
  local username="$1"
  curl -sf --connect-timeout 5 --max-time "$CURL_MAX_TIME" \
    "$KEYCLOAK_URL/admin/realms/$REALM/users?username=$username" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
    | jq -r --arg username "$username" '.[] | select(.username == $username) | .id' \
    | head -n1
}

ensure_realm_role() {
  local role_name="$1"
  local role_http
  role_http=$(curl --connect-timeout 5 --max-time "$CURL_MAX_TIME" -s -o /dev/null -w "%{http_code}" \
    "$KEYCLOAK_URL/admin/realms/$REALM/roles/$role_name" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN")
  if [ "$role_http" = "200" ]; then
    return 0
  fi
  if [ "$role_http" != "404" ]; then
    echo -e "${RED}✗ Failed to inspect realm role $role_name (HTTP $role_http)${NC}"
    exit 1
  fi
  curl -sf --connect-timeout 5 --max-time "$CURL_MAX_TIME" -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/roles" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$role_name\"}" >/dev/null
}

assign_realm_role() {
  local user_id="$1"
  local role_name="$2"
  local role_rep
  role_rep=$(curl -sf --connect-timeout 5 --max-time "$CURL_MAX_TIME" \
    "$KEYCLOAK_URL/admin/realms/$REALM/roles/$role_name" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN")
  curl -sf --connect-timeout 5 --max-time "$CURL_MAX_TIME" -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$user_id/role-mappings/realm" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "[$role_rep]" >/dev/null
}

ensure_admin_app_user() {
  local user_id create_resp create_http
  user_id=$(lookup_user_id_by_username "$ADMIN_APP_USERNAME")
  if [ -z "${user_id:-}" ]; then
    create_resp=$(curl --connect-timeout 5 --max-time "$CURL_MAX_TIME" -s -w "\n%{http_code}" -X POST \
      "$KEYCLOAK_URL/admin/realms/$REALM/users" \
      -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"username\": \"$ADMIN_APP_USERNAME\",
        \"enabled\": true,
        \"emailVerified\": true,
        \"email\": \"admin-dashboard@gantry.local\",
        \"firstName\": \"Admin\",
        \"lastName\": \"Dashboard\"
      }")
    create_http=$(echo "$create_resp" | tail -n1)
    if [ "$create_http" != "201" ] && [ "$create_http" != "409" ]; then
      echo -e "${RED}✗ Failed to create admin user (HTTP $create_http)${NC}"
      echo "$(echo "$create_resp" | sed '$d')"
      exit 1
    fi
    user_id=$(lookup_user_id_by_username "$ADMIN_APP_USERNAME")
  fi

  if [ -z "${user_id:-}" ]; then
    echo -e "${RED}✗ Could not resolve admin user id${NC}"
    exit 1
  fi

  curl -sf --connect-timeout 5 --max-time "$CURL_MAX_TIME" -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$user_id/reset-password" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"type\": \"password\", \"temporary\": false, \"value\": \"$ADMIN_APP_PASSWORD\"}" >/dev/null

  ensure_realm_role "ADMIN"
  assign_realm_role "$user_id" "ADMIN"
}

login_admin_user() {
  ADMIN_AUTH_TOKEN=$(curl -sf --connect-timeout 5 --max-time "$CURL_MAX_TIME" -X POST \
    "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=$ADMIN_CLIENT_ID" \
    -d "username=$ADMIN_APP_USERNAME" \
    -d "password=$ADMIN_APP_PASSWORD" \
    -d "scope=organization email profile" \
    -d "grant_type=password" \
    | jq -r '.access_token // empty')

  if [ -z "${ADMIN_AUTH_TOKEN:-}" ] || [ "$ADMIN_AUTH_TOKEN" = "null" ]; then
    echo -e "${RED}✗ Failed to get admin dashboard token${NC}"
    exit 1
  fi
}

extract_id_or_fail() {
  local label="$1"
  local id
  case "$label" in
    organization)
      id=$(echo "$RESPONSE_BODY" | jq -r '.org_id // empty')
      ;;
    project)
      id=$(echo "$RESPONSE_BODY" | jq -r '.project_uuid // empty')
      ;;
    *)
      id=$(echo "$RESPONSE_BODY" | jq -r '.id // empty')
      ;;
  esac
  if [ -z "$id" ] || [ "$id" = "null" ]; then
    echo -e "${RED}✗ Could not extract $label id from previous response${NC}"
    exit 1
  fi
  echo "$id"
}

extract_api_key_uuid_or_fail() {
  local id
  id=$(echo "$RESPONSE_BODY" | jq -r '.api_key_uuid // empty')
  if [ -z "$id" ] || [ "$id" = "null" ]; then
    echo -e "${RED}✗ Could not extract API key uuid from previous response${NC}"
    exit 1
  fi
  echo "$id"
}

echo "=========================================="
echo "Testing Admin Dashboard E2E CRUD Flow"
echo "=========================================="
echo ""

ensure_master_admin_token
ensure_admin_app_user
login_admin_user

SUFFIX="$(date +%s)"
ORG_NAME="admin-dashboard-org-$SUFFIX"
PROJECT_NAME="admin-dashboard-project-$SUFFIX"

run_test "GET admin current user" 200 \
  "$BASE_URL/me" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "GET admin dashboard summary" 200 \
  "$BASE_URL/dashboard/summary" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "GET admin organization permission catalog" 200 \
  "$BASE_URL/organization-permissions" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "GET admin project permission catalog" 200 \
  "$BASE_URL/project-permissions" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "GET admin API key permission catalog" 200 \
  "$BASE_URL/api-key-permissions" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "POST admin organization" 201 \
  -X POST "$BASE_URL/organizations" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$ORG_NAME\", \"alias\": \"$ORG_NAME\"}"
ORG_ID=$(extract_id_or_fail "organization")

run_test "GET admin organization list" 200 \
  "$BASE_URL/organizations?q=$ORG_NAME" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "GET admin organization by id" 200 \
  "$BASE_URL/organizations/$ORG_ID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "PATCH admin organization" 200 \
  -X PATCH "$BASE_URL/organizations/$ORG_ID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$ORG_NAME-renamed\"}"

run_test "GET admin organization settings" 200 \
  "$BASE_URL/organization-settings/$ORG_ID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "PATCH admin organization settings" 200 \
  -X PATCH "$BASE_URL/organization-settings/$ORG_ID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rate_limit":123,"spending_limit":5000,"extra":{"env":"admin-dashboard"}}'

run_test "GET admin organization users" 200 \
  "$BASE_URL/organization-users?org_id=$ORG_ID&limit=10&offset=0" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "POST admin project" 201 \
  -X POST "$BASE_URL/projects?org_id=$ORG_ID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$PROJECT_NAME\", \"description\": \"admin dashboard e2e\"}"
PROJECT_ID=$(extract_id_or_fail "project")

run_test "GET admin project list" 200 \
  "$BASE_URL/projects?org_id=$ORG_ID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "GET admin project by id" 200 \
  "$BASE_URL/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "PUT admin project" 200 \
  -X PUT "$BASE_URL/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$PROJECT_NAME-renamed\", \"description\": \"updated\"}"

run_test "GET admin project settings" 200 \
  "$BASE_URL/project-settings/$PROJECT_ID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "PATCH admin project settings" 200 \
  -X PATCH "$BASE_URL/project-settings/$PROJECT_ID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rate_limit":77,"spending_limit":9000,"extra":{"env":"admin-dashboard"}}'

run_test "GET admin project users" 200 \
  "$BASE_URL/project-users?project_id=$PROJECT_ID&limit=10&offset=0" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "POST admin API key" 201 \
  -X POST "$BASE_URL/api-keys?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"dashboard-key","description":"admin dashboard e2e","permissions":[]}'
API_KEY_UUID=$(extract_api_key_uuid_or_fail)

run_test "GET admin API key list" 200 \
  "$BASE_URL/api-keys?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "GET admin API key by uuid" 200 \
  "$BASE_URL/api-keys/$API_KEY_UUID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "PUT admin API key" 200 \
  -X PUT "$BASE_URL/api-keys/$API_KEY_UUID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"dashboard-key-renamed","description":"updated","permissions":[]}'

run_test "GET admin user list" 200 \
  "$BASE_URL/users?q=$ADMIN_APP_USERNAME" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "DELETE admin API key" 200 \
  -X DELETE "$BASE_URL/api-keys/$API_KEY_UUID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "DELETE admin project archives it" 200 \
  -X DELETE "$BASE_URL/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "DELETE admin organization requests deletion" 202 \
  -X DELETE "$BASE_URL/organizations/$ORG_ID" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

echo "=========================================="
echo -e "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC} (out of ${TEST_NUM})"
echo "=========================================="

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
