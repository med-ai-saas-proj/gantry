#!/bin/bash
# Test script for Organization API endpoints
# Requires: jq, curl
#
# Optional env:
#   USE_CLEAN_TEST_ACTOR=1 (default)
#   AUTH_TOKEN, ORG_ID when USE_CLEAN_TEST_ACTOR=0

set -euo pipefail

BASE_URL="http://localhost:8000/management/v1/organizations"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Keycloak config (for direct Keycloak API calls)
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-gantry}"
ADMIN_USERNAME="${KEYCLOAK_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
USE_NEW_TEST_USER="${USE_NEW_TEST_USER:-1}"
USE_CLEAN_TEST_ACTOR="${USE_CLEAN_TEST_ACTOR:-1}"

echo "=========================================="
echo "Testing Organization API Endpoints"
echo "=========================================="
echo ""

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

setup_clean_actor_and_org() {
    ensure_admin_token
    REALM_REP=$(curl -sf \
      "$KEYCLOAK_URL/admin/realms/$REALM" \
      -H "Authorization: Bearer $ADMIN_TOKEN")
    UPDATED_REALM=$(echo "$REALM_REP" | jq '.organizationsEnabled = true')
    curl -sf -X PUT \
      "$KEYCLOAK_URL/admin/realms/$REALM" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$UPDATED_REALM" >/dev/null
    ensure_org_permissions_profile_attr

    TEST_USER_SUFFIX="${TEST_USER_SUFFIX:-$(date +%s)}"
    KEYCLOAK_USERNAME="${KEYCLOAK_USERNAME:-org-api-test-${TEST_USER_SUFFIX}}"
    KEYCLOAK_PASSWORD="${KEYCLOAK_PASSWORD:-Test123!${TEST_USER_SUFFIX}}"
    TEST_EMAIL="${TEST_EMAIL:-${KEYCLOAK_USERNAME}@local.test}"

    CREATE_USER_RESP=$(curl -s -w "\n%{http_code}" -X POST \
      "$KEYCLOAK_URL/admin/realms/$REALM/users" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"username\": \"$KEYCLOAK_USERNAME\",
        \"enabled\": true,
        \"emailVerified\": true,
        \"firstName\": \"Org\",
        \"lastName\": \"Tester\",
        \"email\": \"$TEST_EMAIL\"
      }")
    CREATE_USER_HTTP=$(echo "$CREATE_USER_RESP" | tail -n1)
    if [ "$CREATE_USER_HTTP" != "201" ] && [ "$CREATE_USER_HTTP" != "409" ]; then
        echo -e "${RED}✗ Failed to create clean actor (HTTP $CREATE_USER_HTTP)${NC}"
        echo "  Response: $(echo "$CREATE_USER_RESP" | sed '$d')"
        exit 1
    fi

    TEST_USER_ID=$(lookup_user_id_by_username "$KEYCLOAK_USERNAME")
    if [ -z "${TEST_USER_ID:-}" ]; then
        echo -e "${RED}✗ Could not resolve clean actor user id${NC}"
        exit 1
    fi

    curl -sf -X PUT \
      "$KEYCLOAK_URL/admin/realms/$REALM/users/$TEST_USER_ID/reset-password" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"type\": \"password\",
        \"temporary\": false,
        \"value\": \"$KEYCLOAK_PASSWORD\"
      }" >/dev/null

    curl -sf \
      "$KEYCLOAK_URL/admin/realms/$REALM/organizations/members/$TEST_USER_ID/organizations" \
      -H "Authorization: Bearer $ADMIN_TOKEN" 2>/dev/null \
      | jq -r '.[].id // empty' \
      | while read -r old_org_id; do
            [ -z "$old_org_id" ] && continue
            curl -s -o /dev/null -X DELETE \
              "$KEYCLOAK_URL/admin/realms/$REALM/organizations/$old_org_id/members/$TEST_USER_ID" \
              -H "Authorization: Bearer $ADMIN_TOKEN"
        done

    USER_REP=$(curl -sf \
      "$KEYCLOAK_URL/admin/realms/$REALM/users/$TEST_USER_ID" \
      -H "Authorization: Bearer $ADMIN_TOKEN")
    UPDATED_USER_REP=$(echo "$USER_REP" | jq \
      '.attributes.org_permissions = ["organization.owner"]
       | .requiredActions = []
       | .emailVerified = true
       | .firstName = "Org"
       | .lastName = "Tester"')
    curl -sf -X PUT \
      "$KEYCLOAK_URL/admin/realms/$REALM/users/$TEST_USER_ID" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$UPDATED_USER_REP" >/dev/null

    if [ -z "${ORG_ID:-}" ]; then
        ORG_NAME="test-org-$(date +%s)"
        ORG_CREATE_RESP=$(curl -s -w "\n%{http_code}" -X POST \
          "$KEYCLOAK_URL/admin/realms/$REALM/organizations" \
          -H "Authorization: Bearer $ADMIN_TOKEN" \
          -H "Content-Type: application/json" \
          -d "{
            \"name\": \"$ORG_NAME\",
            \"alias\": \"$ORG_NAME\",
            \"enabled\": true
          }")
        ORG_CREATE_HTTP=$(echo "$ORG_CREATE_RESP" | tail -n1)
        if [ "$ORG_CREATE_HTTP" != "201" ] && [ "$ORG_CREATE_HTTP" != "200" ]; then
            echo -e "${RED}✗ Failed to create clean org (HTTP $ORG_CREATE_HTTP)${NC}"
            echo "  Response: $(echo "$ORG_CREATE_RESP" | sed '$d')"
            exit 1
        fi
        ORG_ID=$(curl -sf \
          "$KEYCLOAK_URL/admin/realms/$REALM/organizations?search=$ORG_NAME" \
          -H "Authorization: Bearer $ADMIN_TOKEN" \
          | jq -r --arg org_name "$ORG_NAME" '.[] | select(.name == $org_name) | .id' \
          | head -n1)
    fi

    curl -s -o /dev/null -X POST \
      "$KEYCLOAK_URL/admin/realms/$REALM/organizations/$ORG_ID/members" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "\"$TEST_USER_ID\""

    TOKEN_RESP=$(curl -s -w "\n%{http_code}" -X POST \
      "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "client_id=${CLIENT_ID:-gantry-frontend}" \
      -d "username=$KEYCLOAK_USERNAME" \
      -d "password=$KEYCLOAK_PASSWORD" \
      -d "scope=organization email profile" \
      -d "grant_type=password")
    TOKEN_HTTP=$(echo "$TOKEN_RESP" | tail -n1)
    TOKEN_BODY=$(echo "$TOKEN_RESP" | sed '$d')
    AUTH_TOKEN=$(echo "$TOKEN_BODY" | jq -r '.access_token // empty')
    if [ "$TOKEN_HTTP" != "200" ] || [ -z "${AUTH_TOKEN:-}" ] || [ "$AUTH_TOKEN" = "null" ]; then
        echo -e "${RED}✗ Failed to get clean actor token (HTTP $TOKEN_HTTP)${NC}"
        echo "  Response: $TOKEN_BODY"
        exit 1
    fi
    export AUTH_TOKEN ORG_ID TEST_USER_ID
    echo -e "${GREEN}✓ Using clean actor $KEYCLOAK_USERNAME in org $ORG_ID${NC}"
    echo ""
}

# ----------------------------------------------------------------
# Helper: run a curl test
# ----------------------------------------------------------------
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
    if [ -z "${ADMIN_TOKEN:-}" ] || [ "$ADMIN_TOKEN" = "null" ]; then
        echo -e "${RED}✗ Failed to get Keycloak admin token${NC}"
        exit 1
    fi
}

if [ "$USE_CLEAN_TEST_ACTOR" = "1" ]; then
    setup_clean_actor_and_org
fi

AUTH_TOKEN="${AUTH_TOKEN:-YOUR_AUTH_TOKEN}"

if [ "$AUTH_TOKEN" = "YOUR_AUTH_TOKEN" ]; then
    echo -e "${YELLOW}WARNING: AUTH_TOKEN not set${NC}"
    echo "  export AUTH_TOKEN=\$(cat /tmp/keycloak_token.txt)"
    echo "  # or run: $0 --get-token"
    echo ""
    read -p "Press Enter to continue or Ctrl+C to exit..."
fi

set_org_permissions_attr() {
    local user_id="$1"
    local permissions_json="$2"
    USER_REP=$(curl -sf \
      "$KEYCLOAK_URL/admin/realms/$REALM/users/$user_id" \
      -H "Authorization: Bearer $ADMIN_TOKEN")
    UPDATED_REP=$(echo "$USER_REP" | jq ".attributes.org_permissions = $permissions_json")
    curl -s -o /dev/null -X PUT \
      "$KEYCLOAK_URL/admin/realms/$REALM/users/$user_id" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$UPDATED_REP"
}

echo -e "${BLUE}ORG_ID=$ORG_ID${NC}"
echo ""

TEST_INVITE_EMAIL="${TEST_INVITE_EMAIL:-org-invite-$(date +%s)@testmail.com}"
TEST_ORG_NEW_NAME="${TEST_ORG_NEW_NAME:-test-org-renamed-$(date +%s)}"

# ----------------------------------------------------------------
# Test 1: GET /{org_id}/settings
# ----------------------------------------------------------------
run_test "GET org settings" "200" \
  -X GET "$BASE_URL/$ORG_ID/settings" \
  -H "Authorization: Bearer $AUTH_TOKEN"

# ----------------------------------------------------------------
# Test 2: PATCH /{org_id}/settings
# ----------------------------------------------------------------
run_test "PATCH org settings (set rate_limit=100)" "200" \
  -X PATCH "$BASE_URL/$ORG_ID/settings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"rate_limit": 100, "extra": {"theme": "dark", "lang": "vi"}}'

run_test "PATCH org settings (set rate_limit=null)" "200" \
  -X PATCH "$BASE_URL/$ORG_ID/settings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"rate_limit": null, "extra": {"theme": "dark", "lang": "vi"}}'

run_test "PATCH org settings invalid rate_limit=-1 (should fail 400/422)" "400 422" \
  -X PATCH "$BASE_URL/$ORG_ID/settings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"rate_limit": -1, "extra": {"theme": "dark"}}'

# ----------------------------------------------------------------
# Test 3: GET /{org_id}/settings (verify update)
# ----------------------------------------------------------------
run_test "GET org settings (verify update)" "200" \
  -X GET "$BASE_URL/$ORG_ID/settings" \
  -H "Authorization: Bearer $AUTH_TOKEN"

# ----------------------------------------------------------------
# Test 4: GET /{org_id}/users
# ----------------------------------------------------------------
run_test "GET org users" "200" \
  -X GET "$BASE_URL/$ORG_ID/users?limit=10&offset=0" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "GET org users with query filter" "200" \
  -X GET "$BASE_URL/$ORG_ID/users?limit=10&offset=0&q=admin" \
  -H "Authorization: Bearer $AUTH_TOKEN"

# ----------------------------------------------------------------
# Test 7: POST /{org_id}/invitations (invite user)
# ----------------------------------------------------------------
run_test "POST invite user (may fail w/o SMTP / may conflict)" "200 201 204 409 502" \
  -X POST "$BASE_URL/$ORG_ID/invitations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d "{\"email\": \"$TEST_INVITE_EMAIL\", \"permissions\": [\"organization.invite\"]}"

# ----------------------------------------------------------------
# Test 8: GET /{org_id}/invitations
# ----------------------------------------------------------------
run_test "GET invitations" "200" \
  -X GET "$BASE_URL/$ORG_ID/invitations" \
  -H "Authorization: Bearer $AUTH_TOKEN"

# Extract first invitation ID for further tests
INVITATION_RESPONSE=$(curl -s -X GET "$BASE_URL/$ORG_ID/invitations" \
  -H "Authorization: Bearer $AUTH_TOKEN")
INVITATION_ID=$(echo "$INVITATION_RESPONSE" | jq -r '
  if type == "object" then
    (.results[0].id // empty)
  elif type == "array" then
    (.[0].id // empty)
  else
    empty
  end
' 2>/dev/null)

# ----------------------------------------------------------------
# Test 9: GET /{org_id}/invitations/{invitation_id}
# ----------------------------------------------------------------
if [ -n "$INVITATION_ID" ]; then
    run_test "GET invitation by ID ($INVITATION_ID)" "200" \
      -X GET "$BASE_URL/$ORG_ID/invitations/$INVITATION_ID" \
      -H "Authorization: Bearer $AUTH_TOKEN"
else
    echo -e "${YELLOW}[SKIP] No invitation ID — skipping GET invitation by ID${NC}"
    echo ""
fi

# ----------------------------------------------------------------
# Test 10: POST /{org_id}/invitations/{invitation_id}/resend
# ----------------------------------------------------------------
if [ -n "$INVITATION_ID" ]; then
    run_test "POST resend invitation ($INVITATION_ID)" "200" \
      -X POST "$BASE_URL/$ORG_ID/invitations/$INVITATION_ID/resend" \
      -H "Authorization: Bearer $AUTH_TOKEN"
else
    echo -e "${YELLOW}[SKIP] No invitation ID — skipping resend${NC}"
    echo ""
fi

# ----------------------------------------------------------------
# Test 11: DELETE /{org_id}/invitations/{invitation_id}
# ----------------------------------------------------------------
# Re-fetch invitation ID since resend might have changed it
INVITATION_RESPONSE=$(curl -s -X GET "$BASE_URL/$ORG_ID/invitations" \
  -H "Authorization: Bearer $AUTH_TOKEN")
INVITATION_ID=$(echo "$INVITATION_RESPONSE" | jq -r '.results[0].id // empty' 2>/dev/null)

if [ -n "$INVITATION_ID" ]; then
    run_test "DELETE invitation ($INVITATION_ID)" "200 204" \
      -X DELETE "$BASE_URL/$ORG_ID/invitations/$INVITATION_ID" \
      -H "Authorization: Bearer $AUTH_TOKEN"
else
    echo -e "${YELLOW}[SKIP] No invitation ID — skipping delete${NC}"
    echo ""
fi

# ----------------------------------------------------------------
# Test 12: GET /{org_id}/users/{user_id}/permissions
# ----------------------------------------------------------------
# Use the auth user's own ID if TEST_USER_ID not set
if [ -z "${TEST_USER_ID:-}" ]; then
    TEST_USER_ID=$(AUTH_TOKEN="$AUTH_TOKEN" uv run python - <<'PY'
import os, base64, json
token = os.environ.get("AUTH_TOKEN", "")
parts = token.split(".")
if len(parts) < 2:
    print("")
else:
    p = parts[1] + ("=" * (-len(parts[1]) % 4))
    try:
        payload = json.loads(base64.urlsafe_b64decode(p.encode()))
        print(payload.get("sub", ""))
    except Exception:
        print("")
PY
)
fi

echo -e "${BLUE}TEST_USER_ID=$TEST_USER_ID${NC}"
echo ""

run_test "GET user permissions" "200" \
  -X GET "$BASE_URL/$ORG_ID/users/$TEST_USER_ID/permissions" \
  -H "Authorization: Bearer $AUTH_TOKEN"

# ----------------------------------------------------------------
# Permission and user-story scenarios
# ----------------------------------------------------------------
ensure_admin_token
set_org_permissions_attr "$TEST_USER_ID" '["organization.settings.read"]'

run_test "LIMITED actor GET settings (has organization.settings.read)" "200" \
  -X GET "$BASE_URL/$ORG_ID/settings" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "LIMITED actor PATCH settings (missing write permission -> 403)" "403" \
  -X PATCH "$BASE_URL/$ORG_ID/settings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"rate_limit": 88, "extra": {"role": "limited"}}'

run_test "LIMITED actor GET users list (missing permission -> 403)" "403" \
  -X GET "$BASE_URL/$ORG_ID/users?limit=10&offset=0" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "LIMITED actor invite member (missing permission -> 403)" "403" \
  -X POST "$BASE_URL/$ORG_ID/invitations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d "{\"email\": \"limited-try-$(date +%s)@testmail.com\"}"

run_test "LIMITED actor update org metadata (owner-only -> 403)" "403" \
  -X PATCH "$BASE_URL/$ORG_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"name":"should-not-work"}'

run_test "LIMITED actor DELETE org (owner-only -> 403)" "403" \
  -X DELETE "$BASE_URL/$ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "LIMITED actor read own permissions (self-read allowed)" "200" \
  -X GET "$BASE_URL/$ORG_ID/users/$TEST_USER_ID/permissions" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "LIMITED actor update own permissions (missing read_write -> 403)" "403" \
  -X PUT "$BASE_URL/$ORG_ID/users/$TEST_USER_ID/permissions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"permissions": ["organization.settings.read", "organization.settings.write"]}'

set_org_permissions_attr "$TEST_USER_ID" '["organization.owner"]'

run_test "OWNER hierarchy allows GET users list (via organization.owner)" "200" \
  -X GET "$BASE_URL/$ORG_ID/users?limit=10&offset=0" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "OWNER hierarchy allows GET settings (via organization.owner -> settings.read)" "200" \
  -X GET "$BASE_URL/$ORG_ID/settings" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "OWNER hierarchy allows PATCH settings (via organization.owner -> settings.write)" "200" \
  -X PATCH "$BASE_URL/$ORG_ID/settings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"rate_limit": 91, "extra": {"hierarchy": "settings-write"}}'

run_test "OWNER hierarchy allows GET invitations (via organization.owner -> invite)" "200" \
  -X GET "$BASE_URL/$ORG_ID/invitations" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "OWNER hierarchy allows DELETE user route (via organization.owner -> users.remove)" "403 404" \
  -X DELETE "$BASE_URL/$ORG_ID/users/00000000-0000-0000-0000-000000000000" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "OWNER hierarchy allows PUT user permissions (via organization.owner)" "200" \
  -X PUT "$BASE_URL/$ORG_ID/users/$TEST_USER_ID/permissions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"permissions": ["organization.owner", "organization.settings.read"]}'

run_test "OWNER hierarchy allows PUT permissions route (via organization.owner -> users.permissions.read_write)" "404" \
  -X PUT "$BASE_URL/$ORG_ID/users/00000000-0000-0000-0000-000000000000/permissions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"permissions": ["organization.settings.read"]}'

run_test "OWNER actor PATCH settings after owner restore (should pass 200)" "200" \
  -X PATCH "$BASE_URL/$ORG_ID/settings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"rate_limit": 90, "extra": {"role": "limited-granted"}}'

run_test "OWNER actor invite member after owner restore (should pass 200/201/204/409/502)" "200 201 204 409 502" \
  -X POST "$BASE_URL/$ORG_ID/invitations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d "{\"email\": \"limited-granted-$(date +%s)@testmail.com\"}"

run_test "DELETE owner user from org (should fail 403)" "403" \
  -X DELETE "$BASE_URL/$ORG_ID/users/$TEST_USER_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "DELETE non-existent user from org (should fail 403/404)" "403 404" \
  -X DELETE "$BASE_URL/$ORG_ID/users/00000000-0000-0000-0000-000000000000" \
  -H "Authorization: Bearer $AUTH_TOKEN"

# ----------------------------------------------------------------
# Test 13: PUT /{org_id}/users/{user_id}/permissions
# ----------------------------------------------------------------
run_test "PUT update user permissions" "200" \
  -X PUT "$BASE_URL/$ORG_ID/users/$TEST_USER_ID/permissions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"permissions": ["organization.owner", "organization.invite", "organization.settings.read"]}'

# ----------------------------------------------------------------
# Test 14: PUT invalid permissions (should fail)
# ----------------------------------------------------------------
run_test "PUT invalid permissions (should fail 400)" "400" \
  -X PUT "$BASE_URL/$ORG_ID/users/$TEST_USER_ID/permissions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"permissions": ["organization.owner", "bogus.permission"]}'

# ----------------------------------------------------------------
# Additional validation and edge-case scenarios
# ----------------------------------------------------------------
run_test "GET users with invalid limit=0 (should fail 400/422)" "400 422" \
  -X GET "$BASE_URL/$ORG_ID/users?limit=0&offset=0" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "GET users with invalid offset=-1 (should fail 400/422)" "400 422" \
  -X GET "$BASE_URL/$ORG_ID/users?limit=10&offset=-1" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "PATCH org metadata with empty name (should fail 400/422)" "400 422" \
  -X PATCH "$BASE_URL/$ORG_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"name": ""}'

run_test "GET invitation invalid id (should fail 404)" "404" \
  -X GET "$BASE_URL/$ORG_ID/invitations/does-not-exist" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "POST resend invalid invitation id (should fail 404/502)" "404 502" \
  -X POST "$BASE_URL/$ORG_ID/invitations/does-not-exist/resend" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "DELETE invalid invitation id (should fail 404)" "404" \
  -X DELETE "$BASE_URL/$ORG_ID/invitations/does-not-exist" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "PUT owner permissions without owner (should fail 403)" "403" \
  -X PUT "$BASE_URL/$ORG_ID/users/$TEST_USER_ID/permissions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"permissions": ["organization.invite"]}'

run_test "PUT permissions missing body field (should fail 400/422)" "400 422" \
  -X PUT "$BASE_URL/$ORG_ID/users/$TEST_USER_ID/permissions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"permissionz": ["organization.owner"]}'

# ----------------------------------------------------------------
# More API validation and not-found scenarios
# ----------------------------------------------------------------
run_test "GET users with limit too high (should fail 400/422)" "400 422" \
  -X GET "$BASE_URL/$ORG_ID/users?limit=101&offset=0" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "PATCH settings with invalid extra type (should fail 400/422)" "400 422" \
  -X PATCH "$BASE_URL/$ORG_ID/settings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"rate_limit": 100, "extra": ["not-a-dict"]}'

run_test "POST invitation with invalid email (should fail 400/422)" "400 422" \
  -X POST "$BASE_URL/$ORG_ID/invitations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"email": "not-an-email"}'

LONG_NAME=$(printf 'x%.0s' $(seq 1 300))
run_test "PATCH org metadata with too-long name (should fail 400/422)" "400 422" \
  -X PATCH "$BASE_URL/$ORG_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d "{\"name\": \"$LONG_NAME\"}"

FAKE_ORG_ID="00000000-0000-0000-0000-000000000000"
run_test "GET metadata for non-existent org (should fail 403/404)" "403 404" \
  -X GET "$BASE_URL/$FAKE_ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "GET settings for non-existent org (should fail 403/404)" "403 404" \
  -X GET "$BASE_URL/$FAKE_ORG_ID/settings" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "GET settings with malformed token (should fail 401/403)" "401 403" \
  -X GET "$BASE_URL/$ORG_ID/settings" \
  -H "Authorization: Bearer malformed.token.value"

# ----------------------------------------------------------------
# Test 15: GET /{org_id} (metadata)
# ----------------------------------------------------------------
run_test "GET org metadata" "200" \
  -X GET "$BASE_URL/$ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

# ----------------------------------------------------------------
# Test 16: PATCH /{org_id} (metadata)
# ----------------------------------------------------------------
run_test "PATCH org metadata (rename)" "200" \
  -X PATCH "$BASE_URL/$ORG_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d "{\"name\": \"$TEST_ORG_NEW_NAME\"}"

# ----------------------------------------------------------------
# Test 17: GET /{org_id} (metadata verify rename)
# ----------------------------------------------------------------
run_test "GET org metadata (verify rename)" "200" \
  -X GET "$BASE_URL/$ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

# ----------------------------------------------------------------
# Test 18: DELETE /{org_id} (request deletion)
# ----------------------------------------------------------------
run_test "DELETE org (request deletion)" "202" \
  -X DELETE "$BASE_URL/$ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

# ----------------------------------------------------------------
# Test 19: POST /{org_id}/deletion/cancel
# ----------------------------------------------------------------
run_test "Cancel org deletion request" "200" \
  -X POST "$BASE_URL/$ORG_ID/deletion/cancel" \
  -H "Authorization: Bearer $AUTH_TOKEN"

# ----------------------------------------------------------------
# Test 20: DELETE /{org_id} after cancel (should accept again)
# ----------------------------------------------------------------
run_test "DELETE org after cancel (request deletion again)" "202" \
  -X DELETE "$BASE_URL/$ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

# ----------------------------------------------------------------
# Test 21: DELETE /{org_id} again (should conflict 409)
# ----------------------------------------------------------------
run_test "DELETE org again (should fail 409)" "409" \
  -X DELETE "$BASE_URL/$ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

# ----------------------------------------------------------------
# Test 22: No auth (should fail 401/403)
# ----------------------------------------------------------------
run_test "GET settings without auth (should fail)" "401 403" \
  -X GET "$BASE_URL/$ORG_ID/settings"

# ----------------------------------------------------------------
# Summary
# ----------------------------------------------------------------
echo "=========================================="
echo -e "Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC} (out of $TEST_NUM)"
echo "=========================================="
echo ""

if [ -n "${ORG_NAME:-}" ]; then
    echo -e "${YELLOW}Cleanup: delete org '$ORG_NAME' from Keycloak admin console${NC}"
    echo "  or run:"
    echo "  curl -X DELETE \"$KEYCLOAK_URL/admin/realms/$REALM/organizations/$ORG_ID\" \\"
    echo "    -H \"Authorization: Bearer \$ADMIN_TOKEN\""
fi

exit $FAIL
