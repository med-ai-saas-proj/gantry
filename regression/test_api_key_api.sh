#!/bin/bash
# Test script for project-scoped API key management endpoints.

set -euo pipefail

BASE_URL="http://localhost:8000/management/v1/api-keys"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-gantry}"
CLIENT_ID="${CLIENT_ID:-gantry-frontend}"
ADMIN_USERNAME="${KEYCLOAK_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

TEST_NUM=0
PASS=0
FAIL=0
HTTP_CODE=""
RESPONSE_BODY=""

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

ensure_project_permissions_profile_attr() {
  PROFILE=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/profile" \
    -H "Authorization: Bearer $ADMIN_TOKEN" 2>/dev/null || echo '{}')
  if echo "$PROFILE" | jq -e '.attributes[] | select(.name == "project_permissions")' >/dev/null 2>&1; then
    return 0
  fi
  UPDATED_PROFILE=$(echo "$PROFILE" | jq '.attributes += [{
    "name": "project_permissions",
    "displayName": "Project Permissions",
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

set_project_permissions_attr() {
  local user_id="$1"
  local project_id="$2"
  local permissions_json="$3"
  local attr_key="project_permissions"
  local user_rep updated_user_rep
  local existing combined

  existing=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$user_id" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    | jq -c '
      .attributes.project_permissions as $raw
      | if ($raw | type) == "object" then $raw
        elif ($raw | type) == "array" then reduce ($raw[]? | fromjson? // {}) as $item ({}; . + $item)
        elif ($raw | type) == "string" then ($raw | fromjson? // {})
        else {}
        end')
  combined=$(jq -cn \
    --arg project_id "$project_id" \
    --argjson existing "$existing" \
    --argjson permissions "$permissions_json" \
    '$existing + {($project_id): $permissions}')

  user_rep=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$user_id" \
    -H "Authorization: Bearer $ADMIN_TOKEN")
  updated_user_rep=$(echo "$user_rep" | jq \
    --arg attr_key "$attr_key" \
    --argjson permissions "$combined" \
    '.attributes[$attr_key] = ($permissions | to_entries | map({(.key): .value} | tojson))')
  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$user_id" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$updated_user_rep" >/dev/null
}

reset_password() {
  local user_id="$1"
  local password="$2"
  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$user_id/reset-password" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"type\": \"password\",
      \"temporary\": false,
      \"value\": \"$password\"
    }" >/dev/null
}

login_user() {
  local username="$1"
  local password="$2"
  curl -sf -X POST \
    "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=$CLIENT_ID" \
    -d "username=$username" \
    -d "password=$password" \
    -d "scope=organization email profile" \
    -d "grant_type=password" \
    | jq -r '.access_token // empty'
}

setup_clean_actor_and_org() {
  ensure_admin_token
  ensure_org_permissions_profile_attr
  ensure_project_permissions_profile_attr

  local suffix
  suffix="$(date +%s)"
  ACTOR_USERNAME="apikey-api-owner-${suffix}"
  ACTOR_PASSWORD="Test123!${suffix}"
  ACTOR_EMAIL="${ACTOR_USERNAME}@local.test"

  curl -s -o /dev/null -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/users" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"$ACTOR_USERNAME\",
      \"enabled\": true,
      \"emailVerified\": true,
      \"email\": \"$ACTOR_EMAIL\"
    }"

  ACTOR_USER_ID=$(lookup_user_id_by_username "$ACTOR_USERNAME")
  reset_password "$ACTOR_USER_ID" "$ACTOR_PASSWORD"

  USER_REP=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$ACTOR_USER_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN")
  UPDATED_USER_REP=$(echo "$USER_REP" | jq \
    '.attributes.org_permissions = ["organization.owner"]
     | .requiredActions = []
     | .emailVerified = true')
  UPDATED_USER_REP=$(echo "$UPDATED_USER_REP" | jq \
    '.firstName = "ApiKey"
     | .lastName = "Owner"')
  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$ACTOR_USER_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$UPDATED_USER_REP" >/dev/null

  ORG_NAME="apikey-api-org-${suffix}"
  curl -sf -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/organizations" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"$ORG_NAME\",
      \"alias\": \"$ORG_NAME\",
      \"enabled\": true
    }" >/dev/null

  ORG_ID=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/organizations?search=$ORG_NAME" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    | jq -r --arg org_name "$ORG_NAME" '.[] | select(.name == $org_name) | .id' \
    | head -n1)

  curl -s -o /dev/null -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/organizations/$ORG_ID/members" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "\"$ACTOR_USER_ID\""

  AUTH_TOKEN=$(login_user "$ACTOR_USERNAME" "$ACTOR_PASSWORD")
  if [ -z "$AUTH_TOKEN" ]; then
    echo -e "${RED}✗ Failed to get owner auth token${NC}"
    exit 1
  fi
}

bootstrap_project() {
  PROJECT_ID=$(GANTRY_SERVER__CONFIG_FILE=gantry.toml \
    PYTHONPATH=src \
    DEBUG=1 \
    UV_ENV_FILE=.env \
    ORG_ID="$ORG_ID" \
    ACTOR_USER_ID="$ACTOR_USER_ID" \
    BOOTSTRAP_PROJECT_NAME="apikey-api-project-$(date +%s)" \
    uv run python - <<'PY' | tail -n1
import asyncio
import os

from gantry.db.factories import getSessionManager
from gantry.management.project.models import Project
from gantry.management.project.repositories import ProjectMemberRepository
from gantry.shared.utils.uuid_utils import uuid7


async def main():
    org_id = os.environ["ORG_ID"]
    actor_user_id = os.environ["ACTOR_USER_ID"]
    project_name = os.environ["BOOTSTRAP_PROJECT_NAME"]
    session_manager = getSessionManager()
    member_repo = ProjectMemberRepository()

    async with session_manager.get_session() as session:
        project = Project(
            name=project_name,
            description="bootstrap project for api key tests",
            organization_id=org_id,
        )
        project.uuid = uuid7()
        session.add(project)
        await session.flush()
        await member_repo.upsertMembership(
            session=session,
            project_id=project.id,
            user_id=actor_user_id,
        )
        await session.commit()
        print(project.uuid)


asyncio.run(main())
PY
)

  set_project_permissions_attr \
    "$ACTOR_USER_ID" \
    "$PROJECT_ID" \
    '["project.owner","apikey.read","apikey.write"]'
}

create_readonly_member() {
  local suffix
  suffix="$(date +%s)"
  READONLY_USERNAME="apikey-api-readonly-${suffix}"
  READONLY_PASSWORD="Test123!${suffix}"
  READONLY_EMAIL="${READONLY_USERNAME}@local.test"

  curl -s -o /dev/null -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/users" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"$READONLY_USERNAME\",
      \"enabled\": true,
      \"emailVerified\": true,
      \"email\": \"$READONLY_EMAIL\"
    }"

  READONLY_USER_ID=$(lookup_user_id_by_username "$READONLY_USERNAME")
  reset_password "$READONLY_USER_ID" "$READONLY_PASSWORD"

  USER_REP=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$READONLY_USER_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN")
  UPDATED_USER_REP=$(echo "$USER_REP" | jq \
    '.requiredActions = []
     | .emailVerified = true
     | .firstName = "ApiKey"
     | .lastName = "Reader"')
  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$READONLY_USER_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$UPDATED_USER_REP" >/dev/null

  curl -s -o /dev/null -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/organizations/$ORG_ID/members" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "\"$READONLY_USER_ID\""

  GANTRY_SERVER__CONFIG_FILE=gantry.toml \
    PYTHONPATH=src DEBUG=1 UV_ENV_FILE=.env \
    PROJECT_ID="$PROJECT_ID" READONLY_USER_ID="$READONLY_USER_ID" \
    uv run python - <<'PY' >/dev/null
import asyncio
import os
from gantry.db.factories import getSessionManager
from gantry.management.project.repositories import ProjectMemberRepository
from gantry.management.project.models import Project
from sqlalchemy import select


async def main():
    project_uuid = os.environ["PROJECT_ID"]
    user_id = os.environ["READONLY_USER_ID"]
    session_manager = getSessionManager()
    member_repo = ProjectMemberRepository()
    async with session_manager.get_session() as session:
        project = await member_repo.selectOne(
            session,
            select(Project).select_from(Project).where(Project.uuid == project_uuid),
        )
        await member_repo.upsertMembership(
            session=session,
            project_id=project.id,
            user_id=user_id,
        )
        await session.commit()


asyncio.run(main())
PY

  set_project_permissions_attr \
    "$READONLY_USER_ID" \
    "$PROJECT_ID" \
    '["apikey.read"]'

  READONLY_AUTH_TOKEN=$(login_user "$READONLY_USERNAME" "$READONLY_PASSWORD")
  if [ -z "$READONLY_AUTH_TOKEN" ]; then
    echo -e "${RED}✗ Failed to get readonly auth token${NC}"
    exit 1
  fi
}


echo "=========================================="
echo "Testing API Key Management Endpoints"
echo "=========================================="
echo ""

setup_clean_actor_and_org
bootstrap_project
create_readonly_member

echo -e "${BLUE}ORG_ID=$ORG_ID${NC}"
echo -e "${BLUE}PROJECT_ID=$PROJECT_ID${NC}"
echo -e "${BLUE}ACTOR_USER_ID=$ACTOR_USER_ID${NC}"
echo -e "${BLUE}READONLY_USER_ID=$READONLY_USER_ID${NC}"
echo ""

run_test "GET api key permission catalog" "200" \
  -X GET "$BASE_URL/permissions" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "GET api key permission audit" "200" \
  -X GET "$BASE_URL/permissions/audit" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "GET api keys missing project query (should fail 400/422)" "400 422" \
  -X GET "$BASE_URL" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "GET api keys in project (initial empty list)" "200" \
  -X GET "$BASE_URL?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "POST create api key invalid permission (should fail 400)" "400" \
  -X POST "$BASE_URL?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"invalid-key","description":"invalid","permissions":["unknown.permission"]}'

run_test "POST create api key with registered permission" "201" \
  -X POST "$BASE_URL?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"project-key","description":"created by shell test","permissions":["file.read"]}'

APIKEY_UUID=$(echo "$RESPONSE_BODY" | jq -r '.api_key_uuid // empty')
RAW_API_KEY=$(echo "$RESPONSE_BODY" | jq -r '.key // empty')

run_test "GET api keys in project after create" "200" \
  -X GET "$BASE_URL?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "GET api key by uuid" "200" \
  -X GET "$BASE_URL/$APIKEY_UUID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "PUT update api key permissions and metadata" "200" \
  -X PUT "$BASE_URL/$APIKEY_UUID" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"project-key-updated","description":"updated by shell test","permissions":["file.read"]}'

run_test "GET api key by uuid after update" "200" \
  -X GET "$BASE_URL/$APIKEY_UUID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "POST disable api key" "200" \
  -X POST "$BASE_URL/$APIKEY_UUID/disable" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "GET api key by uuid after disable" "200" \
  -X GET "$BASE_URL/$APIKEY_UUID" \
  -H "Authorization: Bearer $AUTH_TOKEN"
TEST_NUM=$((TEST_NUM + 1))
echo -e "${CYAN}[TEST $TEST_NUM] Disabled flag should be true after disable${NC}"
if [ "$(echo "$RESPONSE_BODY" | jq -r '.disabled // false')" = "true" ]; then
  echo -e "  ${GREEN}✓ PASS${NC}"
  PASS=$((PASS + 1))
else
  echo -e "  ${RED}✗ FAIL (expected disabled=true)${NC}"
  FAIL=$((FAIL + 1))
fi
echo ""

run_test "POST enable api key" "200" \
  -X POST "$BASE_URL/$APIKEY_UUID/enable" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "GET api key by uuid after enable" "200" \
  -X GET "$BASE_URL/$APIKEY_UUID" \
  -H "Authorization: Bearer $AUTH_TOKEN"
TEST_NUM=$((TEST_NUM + 1))
echo -e "${CYAN}[TEST $TEST_NUM] Disabled flag should be false after enable${NC}"
if [ "$(echo "$RESPONSE_BODY" | jq -r '.disabled')" = "false" ]; then
  echo -e "  ${GREEN}✓ PASS${NC}"
  PASS=$((PASS + 1))
else
  echo -e "  ${RED}✗ FAIL (expected disabled=false)${NC}"
  FAIL=$((FAIL + 1))
fi
echo ""

run_test "READONLY actor can list api keys" "200" \
  -X GET "$BASE_URL?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $READONLY_AUTH_TOKEN"

run_test "READONLY actor cannot create api key" "403" \
  -X POST "$BASE_URL?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $READONLY_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"should-fail","description":"readonly actor","permissions":["file.read"]}'

run_test "READONLY actor cannot update api key" "403" \
  -X PUT "$BASE_URL/$APIKEY_UUID" \
  -H "Authorization: Bearer $READONLY_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"should-fail","description":"readonly actor","permissions":["file.read"]}'

run_test "DELETE api key" "200" \
  -X DELETE "$BASE_URL/$APIKEY_UUID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "GET deleted api key should return 404" "404" \
  -X GET "$BASE_URL/$APIKEY_UUID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "GET api key without auth (should fail 401/403)" "401 403" \
  -X GET "$BASE_URL/$APIKEY_UUID"

echo "=========================================="
echo -e "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC} (out of ${TEST_NUM})"
echo "=========================================="
echo ""

if [ -n "${RAW_API_KEY:-}" ]; then
  echo -e "${YELLOW}Created raw API key for inspection:${NC} $RAW_API_KEY"
fi

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
