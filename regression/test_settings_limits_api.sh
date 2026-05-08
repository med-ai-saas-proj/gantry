#!/bin/bash
# Focused E2E test for org/project settings RPM + spending-limit roundtrip.

set -euo pipefail

ORG_BASE_URL="http://localhost:8000/management/v1/organizations"
PROJECT_BASE_URL="http://localhost:8000/management/v1/projects"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-gantry}"
CLIENT_ID="${CLIENT_ID:-gantry-frontend}"
ADMIN_USERNAME="${KEYCLOAK_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

TEST_NUM=0
PASS=0
FAIL=0
HTTP_CODE=""
RESPONSE_BODY=""
AUTH_TOKEN=""
ADMIN_TOKEN=""
ORG_ID=""
PROJECT_UUID=""
ACTOR_USER_ID=""

run_test() {
  local description="$1"
  local expected_codes="$2"
  shift 2

  TEST_NUM=$((TEST_NUM + 1))
  echo -e "${CYAN}[TEST $TEST_NUM] $description${NC}"

  local response
  response=$(curl -s -w "\n%{http_code}" "$@")
  HTTP_CODE=$(echo "$response" | tail -n1)
  RESPONSE_BODY=$(echo "$response" | sed '$d')

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

assert_last_json() {
  local description="$1"
  local jq_expr="$2"
  TEST_NUM=$((TEST_NUM + 1))
  echo -e "${CYAN}[TEST $TEST_NUM] $description${NC}"
  if echo "$RESPONSE_BODY" | jq -e "$jq_expr" >/dev/null; then
    echo -e "  ${GREEN}✓ PASS${NC}"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}✗ FAIL${NC}"
    echo "  jq assertion: $jq_expr"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "  $RESPONSE_BODY"
    FAIL=$((FAIL + 1))
  fi
  echo ""
}

ensure_admin_token() {
  if [ -n "$ADMIN_TOKEN" ] && [ "$ADMIN_TOKEN" != "null" ]; then
    return 0
  fi
  ADMIN_TOKEN=$(curl -sf -X POST \
    "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=admin-cli" \
    -d "username=$ADMIN_USERNAME" \
    -d "password=$ADMIN_PASSWORD" \
    -d "grant_type=password" | jq -r '.access_token')
  if [ -z "$ADMIN_TOKEN" ] || [ "$ADMIN_TOKEN" = "null" ]; then
    echo -e "${RED}✗ Failed to get Keycloak admin token${NC}"
    exit 1
  fi
}

lookup_user_id_by_username() {
  local username="$1"
  curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users?username=$username" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    | jq -r --arg username "$username" \
      '.[] | select(.username == $username) | .id' \
    | head -n1
}

ensure_org_permissions_profile_attr() {
  local profile
  local updated_profile
  profile=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/profile" \
    -H "Authorization: Bearer $ADMIN_TOKEN" 2>/dev/null || echo '{}')
  if echo "$profile" | jq -e '.attributes[] | select(.name == "org_permissions")' >/dev/null 2>&1; then
    return 0
  fi
  updated_profile=$(echo "$profile" | jq '.attributes += [{
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
    -d "$updated_profile" >/dev/null
}

setup_clean_actor_and_org() {
  ensure_admin_token
  local realm_rep updated_realm
  realm_rep=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM" \
    -H "Authorization: Bearer $ADMIN_TOKEN")
  updated_realm=$(echo "$realm_rep" | jq '.organizationsEnabled = true')
  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$updated_realm" >/dev/null
  ensure_org_permissions_profile_attr

  local suffix username password email create_user_resp create_user_http
  local user_rep updated_user_rep org_name org_create_resp org_create_http
  local token_resp token_http token_body

  suffix="$(date +%s%N)"
  username="settings-limit-test-${suffix}"
  password="Test123!${suffix}"
  email="${username}@local.test"

  create_user_resp=$(curl -s -w "\n%{http_code}" -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/users" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"$username\",
      \"enabled\": true,
      \"emailVerified\": true,
      \"firstName\": \"Settings\",
      \"lastName\": \"Tester\",
      \"email\": \"$email\"
    }")
  create_user_http=$(echo "$create_user_resp" | tail -n1)
  if [ "$create_user_http" != "201" ] && [ "$create_user_http" != "409" ]; then
    echo -e "${RED}✗ Failed to create clean actor (HTTP $create_user_http)${NC}"
    exit 1
  fi

  ACTOR_USER_ID=$(lookup_user_id_by_username "$username")
  if [ -z "$ACTOR_USER_ID" ]; then
    echo -e "${RED}✗ Could not resolve clean actor user id${NC}"
    exit 1
  fi

  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$ACTOR_USER_ID/reset-password" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"type\": \"password\",
      \"temporary\": false,
      \"value\": \"$password\"
    }" >/dev/null

  user_rep=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$ACTOR_USER_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN")
  updated_user_rep=$(echo "$user_rep" | jq \
    '.attributes.org_permissions = ["organization.owner"]
     | .requiredActions = []
     | .emailVerified = true')
  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$ACTOR_USER_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$updated_user_rep" >/dev/null

  org_name="settings-limit-org-${suffix}"
  org_create_resp=$(curl -s -w "\n%{http_code}" -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/organizations" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"$org_name\",
      \"alias\": \"$org_name\",
      \"enabled\": true
    }")
  org_create_http=$(echo "$org_create_resp" | tail -n1)
  if [ "$org_create_http" != "201" ] && [ "$org_create_http" != "200" ]; then
    echo -e "${RED}✗ Failed to create clean org (HTTP $org_create_http)${NC}"
    exit 1
  fi
  ORG_ID=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/organizations?search=$org_name" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    | jq -r --arg org_name "$org_name" '.[] | select(.name == $org_name) | .id' \
    | head -n1)
  if [ -z "$ORG_ID" ]; then
    echo -e "${RED}✗ Could not resolve created organization${NC}"
    exit 1
  fi

  curl -s -o /dev/null -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/organizations/$ORG_ID/members" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "\"$ACTOR_USER_ID\""

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
    echo -e "${RED}✗ Failed to get clean actor token${NC}"
    exit 1
  fi
}

create_project() {
  run_test "Create project for settings roundtrip" "201" \
    -X POST "$PROJECT_BASE_URL?organization=$ORG_ID" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"settings-limit-project","description":"settings roundtrip"}'
  PROJECT_UUID=$(echo "$RESPONSE_BODY" | jq -r '.project_uuid // empty')
  if [ -z "$PROJECT_UUID" ]; then
    echo -e "${RED}✗ Failed to extract project_uuid from create response${NC}"
    exit 1
  fi
}

echo "=========================================="
echo "Testing Settings RPM / Spending Limit API"
echo "=========================================="
echo ""

setup_clean_actor_and_org
create_project

run_test "PATCH org settings with rate_limit + spending_limit" "200" \
  -X PATCH "$ORG_BASE_URL/$ORG_ID/settings" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rate_limit":123,"spending_limit":456789,"extra":{"tier":"pro","flags":{"beta":true}}}'
assert_last_json \
  "Org PATCH response echoes exact limits" \
  '.rate_limit == 123 and .spending_limit == 456789 and .extra.tier == "pro" and .extra["flags.beta"] == true'

run_test "GET org settings returns stored limits" "200" \
  -X GET "$ORG_BASE_URL/$ORG_ID/settings" \
  -H "Authorization: Bearer $AUTH_TOKEN"
assert_last_json \
  "Org GET returns exact limits" \
  '.rate_limit == 123 and .spending_limit == 456789 and .extra.tier == "pro" and .extra["flags.beta"] == true'

run_test "PATCH project settings with rate_limit + spending_limit" "200" \
  -X PATCH "$PROJECT_BASE_URL/$PROJECT_UUID/settings" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rate_limit":77,"spending_limit":888888,"extra":{"routing":{"mode":"fast"},"budget":{"monthly":"strict"}}}'
assert_last_json \
  "Project PATCH response echoes exact limits" \
  '.rate_limit == 77 and .spending_limit == 888888 and .extra["routing.mode"] == "fast" and .extra["budget.monthly"] == "strict"'

run_test "GET project settings returns stored limits" "200" \
  -X GET "$PROJECT_BASE_URL/$PROJECT_UUID/settings" \
  -H "Authorization: Bearer $AUTH_TOKEN"
assert_last_json \
  "Project GET returns exact limits" \
  '.rate_limit == 77 and .spending_limit == 888888 and .extra["routing.mode"] == "fast" and .extra["budget.monthly"] == "strict"'

TOTAL=$((PASS + FAIL))
echo "=========================================="
echo "Results: $PASS passed, $FAIL failed out of $TOTAL"
echo "=========================================="

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
