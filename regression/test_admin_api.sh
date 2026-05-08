#!/bin/bash
# Test script for admin-only management API endpoints.

set -euo pipefail

BASE_URL="http://localhost:8000/management/v1/admin"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-gantry}"
ADMIN_CLIENT_ID="${ADMIN_CLIENT_ID:-gantry-admin}"
USER_CLIENT_ID="${USER_CLIENT_ID:-gantry-admin}"
KEYCLOAK_ADMIN_USERNAME="${KEYCLOAK_ADMIN_USERNAME:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
ADMIN_APP_USERNAME="${ADMIN_APP_USERNAME:-gantry-admin-user}"
ADMIN_APP_PASSWORD="${ADMIN_APP_PASSWORD:-password}"
NON_ADMIN_USERNAME="${NON_ADMIN_USERNAME:-gantry-test-user}"
NON_ADMIN_PASSWORD="${NON_ADMIN_PASSWORD:-password}"
TARGET_USERNAME="${TARGET_USERNAME:-gantry-test-user}"

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

TEST_NUM=0
PASS=0
FAIL=0

run_test() {
  local description="$1"
  local expected_codes="$2"
  shift 2

  TEST_NUM=$((TEST_NUM + 1))
  echo -e "${CYAN}[TEST $TEST_NUM] $description${NC}"

  RESPONSE=$(curl -s -w "\n%{http_code}" "$@")
  HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
  RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')

  echo "  HTTP Status: $HTTP_CODE"
  echo "$RESPONSE_BODY" | jq '.' 2>/dev/null | head -20 || echo "  $RESPONSE_BODY"

  if echo "$expected_codes" | grep -qw "$HTTP_CODE"; then
    echo -e "  ${GREEN}✓ PASS (expected: $expected_codes)${NC}"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}✗ FAIL (expected: $expected_codes, got: $HTTP_CODE)${NC}"
    FAIL=$((FAIL + 1))
  fi
  echo ""
}

login_user() {
  local client_id="$1"
  local username="$2"
  local password="$3"
  curl -sf -X POST \
    "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=$client_id" \
    -d "username=$username" \
    -d "password=$password" \
    -d "scope=organization email profile" \
    -d "grant_type=password" \
    | jq -r '.access_token // empty'
}

ensure_master_admin_token() {
  if [ -n "${MASTER_ADMIN_TOKEN:-}" ] && [ "$MASTER_ADMIN_TOKEN" != "null" ]; then
    return 0
  fi

  MASTER_ADMIN_TOKEN=$(curl -sf -X POST \
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
  curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users?username=$username" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
    | jq -r --arg username "$username" '.[] | select(.username == $username) | .id' \
    | head -n1
}

ensure_realm_role() {
  local role_name="$1"
  local role_http
  role_http=$(curl -s -o /dev/null -w "%{http_code}" \
    "$KEYCLOAK_URL/admin/realms/$REALM/roles/$role_name" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN")
  if [ "$role_http" = "200" ]; then
    return 0
  fi
  if [ "$role_http" != "404" ]; then
    echo -e "${RED}✗ Failed to inspect realm role $role_name (HTTP $role_http)${NC}"
    exit 1
  fi
  curl -sf -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/roles" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$role_name\"}" >/dev/null
}

assign_realm_role() {
  local user_id="$1"
  local role_name="$2"
  local role_rep
  role_rep=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/roles/$role_name" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN")
  curl -sf -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$user_id/role-mappings/realm" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "[$role_rep]" >/dev/null
}

ensure_admin_app_user() {
  local user_id create_resp create_http
  user_id=$(lookup_user_id_by_username "$ADMIN_APP_USERNAME")
  if [ -z "${user_id:-}" ]; then
    create_resp=$(curl -s -w "\n%{http_code}" -X POST \
      "$KEYCLOAK_URL/admin/realms/$REALM/users" \
      -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"username\": \"$ADMIN_APP_USERNAME\",
        \"enabled\": true,
        \"emailVerified\": true,
        \"email\": \"admin-user@gantry.com\",
        \"firstName\": \"Admin\",
        \"lastName\": \"User\"
      }")
    create_http=$(echo "$create_resp" | tail -n1)
    if [ "$create_http" != "201" ] && [ "$create_http" != "409" ]; then
      echo -e "${RED}✗ Failed to create admin app user (HTTP $create_http)${NC}"
      echo "  Response: $(echo "$create_resp" | sed '$d')"
      exit 1
    fi
    user_id=$(lookup_user_id_by_username "$ADMIN_APP_USERNAME")
  fi

  if [ -z "${user_id:-}" ]; then
    echo -e "${RED}✗ Could not resolve admin app user id${NC}"
    exit 1
  fi

  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$user_id/reset-password" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"type\": \"password\",
      \"temporary\": false,
      \"value\": \"$ADMIN_APP_PASSWORD\"
    }" >/dev/null

  ensure_realm_role "ADMIN"
  assign_realm_role "$user_id" "ADMIN"
}

ensure_permissions_profile_attrs() {
  PROFILE=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/profile" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" 2>/dev/null || echo '{}')

  if ! echo "$PROFILE" | jq -e '.attributes[] | select(.name == "org_permissions")' >/dev/null 2>&1; then
    PROFILE=$(echo "$PROFILE" | jq '.attributes += [{
      "name": "org_permissions",
      "displayName": "Organization Permissions",
      "multivalued": true,
      "permissions": {"view": ["admin"], "edit": ["admin"]},
      "validations": {}
    }]')
  fi

  if ! echo "$PROFILE" | jq -e '.attributes[] | select(.name == "project_permissions")' >/dev/null 2>&1; then
    PROFILE=$(echo "$PROFILE" | jq '.attributes += [{
      "name": "project_permissions",
      "displayName": "Project Permissions",
      "multivalued": true,
      "permissions": {"view": ["admin"], "edit": ["admin"]},
      "validations": {}
    }]')
  fi

  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/profile" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PROFILE" >/dev/null
}

seed_target_permissions() {
  TARGET_USER_ID=$(lookup_user_id_by_username "$TARGET_USERNAME")
  if [ -z "${TARGET_USER_ID:-}" ]; then
    local create_resp create_http
    create_resp=$(curl -s -w "\n%{http_code}" -X POST \
      "$KEYCLOAK_URL/admin/realms/$REALM/users" \
      -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"username\": \"$TARGET_USERNAME\",
        \"enabled\": true,
        \"emailVerified\": true,
        \"email\": \"${TARGET_USERNAME}@local.test\",
        \"firstName\": \"Target\",
        \"lastName\": \"User\"
      }")
    create_http=$(echo "$create_resp" | tail -n1)
    if [ "$create_http" != "201" ] && [ "$create_http" != "409" ]; then
      echo -e "${RED}✗ Failed to create target user (HTTP $create_http)${NC}"
      echo "  Response: $(echo "$create_resp" | sed '$d')"
      exit 1
    fi

    TARGET_USER_ID=$(lookup_user_id_by_username "$TARGET_USERNAME")
    if [ -z "${TARGET_USER_ID:-}" ]; then
      echo -e "${RED}✗ Could not resolve target user id for ${TARGET_USERNAME}${NC}"
      exit 1
    fi

    curl -sf -X PUT \
      "$KEYCLOAK_URL/admin/realms/$REALM/users/$TARGET_USER_ID/reset-password" \
      -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"type\": \"password\",
        \"temporary\": false,
        \"value\": \"$NON_ADMIN_PASSWORD\"
      }" >/dev/null
  fi

  USER_REP=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$TARGET_USER_ID" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN")

  UPDATED_USER_REP=$(echo "$USER_REP" | jq '
    .attributes.org_permissions = ["organization.settings.read", "organization.users.get_all"]
    | .attributes.project_permissions = ({
        "demo-project": ["project.owner", "apikey.read"],
        "second-project": ["project.settings.read"]
      } | to_entries | map({(.key): .value} | tojson))')

  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$TARGET_USER_ID" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$UPDATED_USER_REP" >/dev/null
}

bootstrap_non_admin_user() {
  local suffix username password email create_resp create_http
  suffix="$(date +%s)"
  username="admin-api-user-${suffix}"
  password="Test123!${suffix}"
  email="${username}@local.test"

  create_resp=$(curl -s -w "\n%{http_code}" -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/users" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"$username\",
      \"enabled\": true,
      \"emailVerified\": true,
      \"email\": \"$email\",
      \"firstName\": \"AdminApi\",
      \"lastName\": \"User\"
    }")
  create_http=$(echo "$create_resp" | tail -n1)
  if [ "$create_http" != "201" ] && [ "$create_http" != "409" ]; then
    echo -e "${RED}✗ Failed to create non-admin user (HTTP $create_http)${NC}"
    echo "  Response: $(echo "$create_resp" | sed '$d')"
    exit 1
  fi

  NON_ADMIN_USER_ID=$(lookup_user_id_by_username "$username")
  if [ -z "${NON_ADMIN_USER_ID:-}" ]; then
    echo -e "${RED}✗ Could not resolve non-admin user id${NC}"
    exit 1
  fi

  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$NON_ADMIN_USER_ID/reset-password" \
    -H "Authorization: Bearer $MASTER_ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"type\": \"password\",
      \"temporary\": false,
      \"value\": \"$password\"
    }" >/dev/null

  NON_ADMIN_USERNAME="$username"
  NON_ADMIN_PASSWORD="$password"
}

echo "=========================================="
echo "Testing Admin API Endpoints"
echo "=========================================="
echo ""

ensure_master_admin_token
ensure_admin_app_user
ensure_permissions_profile_attrs
seed_target_permissions
bootstrap_non_admin_user

ADMIN_AUTH_TOKEN=$(login_user "$ADMIN_CLIENT_ID" "$ADMIN_APP_USERNAME" "$ADMIN_APP_PASSWORD")
if [ -z "${ADMIN_AUTH_TOKEN:-}" ]; then
  echo -e "${RED}✗ Failed to get admin app token${NC}"
  exit 1
fi

NON_ADMIN_AUTH_TOKEN=$(login_user "$USER_CLIENT_ID" "$NON_ADMIN_USERNAME" "$NON_ADMIN_PASSWORD")
if [ -z "${NON_ADMIN_AUTH_TOKEN:-}" ]; then
  echo -e "${RED}✗ Failed to get non-admin app token${NC}"
  exit 1
fi

run_test "GET admin current user" 200 \
  "$BASE_URL/me" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "GET target user organizations as admin" 200 \
  "$BASE_URL/users/$TARGET_USER_ID/organizations" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "GET target user profile and permissions as admin" 200 \
  "$BASE_URL/users/$TARGET_USER_ID/profile" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "PUT target user permissions as admin" 200 \
  -X PUT "$BASE_URL/users/$TARGET_USER_ID/permissions" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_permissions": [
      "organization.settings.write"
    ],
    "project_permissions": [
      {
        "project_id": "demo-project",
        "permissions": [
          "project.owner"
        ]
      }
    ]
  }'

run_test "DELETE target user permissions as admin" 200 \
  -X DELETE "$BASE_URL/users/$TARGET_USER_ID/permissions" \
  -H "Authorization: Bearer $ADMIN_AUTH_TOKEN"

run_test "GET admin route with non-admin token should be forbidden" 403 \
  "$BASE_URL/me" \
  -H "Authorization: Bearer $NON_ADMIN_AUTH_TOKEN"

run_test "GET admin route without token should be unauthorized" 401 \
  "$BASE_URL/me"

echo "=========================================="
echo -e "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC} (out of ${TEST_NUM})"
echo "=========================================="

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
