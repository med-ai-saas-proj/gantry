#!/bin/bash
# Smoke test for permission catalog endpoints that exist in the current app.

set -euo pipefail

ORG_BASE_URL="http://localhost:8000/management/v1/organizations/permissions"
PROJECT_BASE_URL="http://localhost:8000/management/v1/projects/permissions"
APIKEY_BASE_URL="http://localhost:8000/management/v1/api-keys/permissions"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-gantry}"
CLIENT_ID="${CLIENT_ID:-gantry-frontend}"
ADMIN_USERNAME="${KEYCLOAK_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

TEST_NUM=0
PASS=0
FAIL=0

ensure_admin_token() {
  if [ -n "${ADMIN_TOKEN:-}" ] && [ "$ADMIN_TOKEN" != "null" ]; then
    return 0
  fi
  ADMIN_TOKEN=$(curl -sf -X POST \
    "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=admin-cli" \
    -d "username=$ADMIN_USERNAME" \
    -d "password=$ADMIN_PASSWORD" \
    -d "grant_type=password" | jq -r '.access_token')
}

lookup_user_id_by_username() {
  local username="$1"
  curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users?username=$username" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    | jq -r --arg username "$username" '.[] | select(.username == $username) | .id' \
    | head -n1
}

ensure_org_permissions_profile_attr() {
  PROFILE=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/profile" \
    -H "Authorization: Bearer $ADMIN_TOKEN" 2>/dev/null || echo '{}')
  if echo "$PROFILE" | jq -e '.attributes[] | select(.name == "org_permissions")' >/dev/null 2>&1; then
    return 0
  fi
  UPDATED_PROFILE=$(echo "$PROFILE" | jq '.attributes += [{
    "name": "org_permissions",
    "displayName": "Organization Permissions",
    "multivalued": true,
    "permissions": {"view": ["admin"], "edit": ["admin"]},
    "validations": {}
  }]')
  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/profile" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$UPDATED_PROFILE" >/dev/null
}

setup_auth_token() {
  if [ -n "${AUTH_TOKEN:-}" ] && [ "$AUTH_TOKEN" != "null" ]; then
    return 0
  fi

  ensure_admin_token
  ensure_org_permissions_profile_attr

  local suffix username password email org_name user_rep updated_user_rep token_resp token_http token_body
  suffix="$(date +%s)"
  username="permission-catalog-${suffix}"
  password="Test123!${suffix}"
  email="${username}@local.test"
  org_name="permission-org-${suffix}"

  curl -s -o /dev/null -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/users" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$username\", \"enabled\": true, \"emailVerified\": true, \"email\": \"$email\"}"

  USER_ID=$(lookup_user_id_by_username "$username")
  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$USER_ID/reset-password" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"type\": \"password\", \"temporary\": false, \"value\": \"$password\"}" >/dev/null

  user_rep=$(curl -sf "$KEYCLOAK_URL/admin/realms/$REALM/users/$USER_ID" -H "Authorization: Bearer $ADMIN_TOKEN")
  updated_user_rep=$(echo "$user_rep" | jq '.attributes.org_permissions = ["organization.owner"] | .requiredActions = [] | .emailVerified = true | .firstName = "Permission" | .lastName = "Catalog"')
  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$USER_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$updated_user_rep" >/dev/null

  curl -sf -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/organizations" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$org_name\", \"alias\": \"$org_name\", \"enabled\": true}" >/dev/null

  ORG_ID=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/organizations?search=$org_name" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    | jq -r --arg org_name "$org_name" '.[] | select(.name == $org_name) | .id' | head -n1)

  curl -s -o /dev/null -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/organizations/$ORG_ID/members" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "\"$USER_ID\""

  token_resp=$(curl -s -w "\n%{http_code}" -X POST \
    "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=$CLIENT_ID" \
    -d "username=$username" \
    -d "password=$password" \
    -d "scope=organization email profile" \
    -d "grant_type=password")
  token_http=$(echo "$token_resp" | tail -n1)
  token_body=$(echo "$token_resp" | sed '$d')
  AUTH_TOKEN=$(echo "$token_body" | jq -r '.access_token // empty')
  if [ "$token_http" != "200" ] || [ -z "$AUTH_TOKEN" ]; then
    echo -e "${RED}✗ Failed to bootstrap AUTH_TOKEN for permission catalog test${NC}"
    echo "$token_body"
    exit 1
  fi
}

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

echo "=========================================="
echo "Testing Permission Catalog Endpoints"
echo "=========================================="
echo ""

setup_auth_token

run_test "GET organization permission catalog" 200 "$ORG_BASE_URL"
run_test "GET project permission catalog" 200 "$PROJECT_BASE_URL"
run_test "GET API key permission catalog" 200 "$APIKEY_BASE_URL" -H "Authorization: Bearer $AUTH_TOKEN"
run_test "GET organization permission catalog with wrong method" "405" -X POST "$ORG_BASE_URL"
run_test "GET project permission catalog with wrong method" "405" -X POST "$PROJECT_BASE_URL"
run_test "GET API key permission catalog with wrong method" "405" -X POST "$APIKEY_BASE_URL"

echo "=========================================="
echo -e "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC} (out of ${TEST_NUM})"
echo "=========================================="

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
