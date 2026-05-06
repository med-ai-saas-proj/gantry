#!/bin/bash
# Frontend-style smoke test for auth + organization + project flows.
# The flow mirrors what the frontend actually does:
# 1. Log in with username/password against Keycloak
# 2. Use the returned access token to call org/project APIs
# 3. Verify backend auth context resolves org_id correctly
#
# Dependencies: curl, jq, uv
# Assumes API server is running at localhost:8000

set -euo pipefail

ORG_BASE_URL="http://localhost:8000/management/v1/organizations"
PROJECT_BASE_URL="http://localhost:8000/management/v1/projects"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-gantry}"
CLIENT_ID="${CLIENT_ID:-gantry-frontend}"
SERVICE_CLIENT_ID="${KEYCLOAK_SERVICE_CLIENT_ID:-gantry-backend}"
SERVICE_CLIENT_SECRET="${KEYCLOAK_SERVICE_CLIENT_SECRET:-}"
ADMIN_USERNAME="${KEYCLOAK_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
CURL_MAX_TIME="${CURL_MAX_TIME:-30}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

TEST_NUM=0
PASS=0
FAIL=0

print_header() {
  echo "===================================================="
  echo "Frontend Auth + Org + Project Smoke Test"
  echo "===================================================="
  echo ""
}

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

preflight_checks() {
  local kc_code api_code

  kc_code=$(curl --connect-timeout 5 --max-time 10 -s -o /dev/null -w '%{http_code}' \
    "$KEYCLOAK_URL/realms/$REALM/.well-known/openid-configuration" || true)
  if [ "$kc_code" != "200" ]; then
    echo -e "${RED}✗ Keycloak is not reachable at $KEYCLOAK_URL for realm $REALM (HTTP $kc_code)${NC}"
    exit 1
  fi

  api_code=$(curl --connect-timeout 5 --max-time 10 -s -o /dev/null -w '%{http_code}' \
    "$ORG_BASE_URL/permissions" || true)
  if [ "$api_code" != "200" ]; then
    echo -e "${RED}✗ API server is not reachable at http://localhost:8000 (HTTP $api_code on /organizations/permissions)${NC}"
    echo "  Start it in another terminal with:"
    echo "  GANTRY_SERVER__CONFIG_FILE=gantry.toml PYTHONPATH=src uv run uvicorn gantry.main.app:main_app --host 0.0.0.0 --port 8000 --env-file .env"
    exit 1
  fi
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

ensure_user_profile_attr() {
  local attr_name="$1"
  local display_name="$2"

  PROFILE=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/profile" \
    -H "Authorization: Bearer $ADMIN_TOKEN" 2>/dev/null || echo '{}')
  if echo "$PROFILE" | jq -e ".attributes[] | select(.name == \"$attr_name\")" >/dev/null 2>&1; then
    return 0
  fi
  UPDATED_PROFILE=$(echo "$PROFILE" | jq --arg attr_name "$attr_name" --arg display_name "$display_name" \
    '.attributes += [{
      "name": $attr_name,
      "displayName": $display_name,
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
  local user_rep updated_user_rep existing combined

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
    --argjson permissions "$combined" \
    '.attributes.project_permissions = ($permissions | to_entries | map({(.key): .value} | tojson))')
  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$user_id" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$updated_user_rep" >/dev/null
}

setup_frontend_actor() {
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

  ensure_user_profile_attr "org_permissions" "Organization Permissions"
  ensure_user_profile_attr "project_permissions" "Project Permissions"

  TEST_SUFFIX="${TEST_SUFFIX:-$(date +%s)}"
  FRONTEND_USERNAME="${FRONTEND_USERNAME:-frontend-e2e-${TEST_SUFFIX}}"
  FRONTEND_PASSWORD="${FRONTEND_PASSWORD:-Test123!${TEST_SUFFIX}}"
  FRONTEND_EMAIL="${FRONTEND_EMAIL:-${FRONTEND_USERNAME}@local.test}"
  MEMBER_USERNAME="${MEMBER_USERNAME:-frontend-member-${TEST_SUFFIX}}"
  MEMBER_EMAIL="${MEMBER_EMAIL:-${MEMBER_USERNAME}@local.test}"

  CREATE_USER_RESP=$(curl -s -w "\n%{http_code}" -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/users" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"$FRONTEND_USERNAME\",
      \"enabled\": true,
      \"emailVerified\": true,
      \"firstName\": \"Frontend\",
      \"lastName\": \"Actor\",
      \"email\": \"$FRONTEND_EMAIL\"
    }")
  CREATE_USER_HTTP=$(echo "$CREATE_USER_RESP" | tail -n1)
  if [ "$CREATE_USER_HTTP" != "201" ] && [ "$CREATE_USER_HTTP" != "409" ]; then
    echo -e "${RED}✗ Failed to create frontend actor${NC}"
    exit 1
  fi

  ACTOR_USER_ID=$(lookup_user_id_by_username "$FRONTEND_USERNAME")
  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$ACTOR_USER_ID/reset-password" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"type\": \"password\",
      \"temporary\": false,
      \"value\": \"$FRONTEND_PASSWORD\"
    }" >/dev/null

  curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/organizations/members/$ACTOR_USER_ID/organizations" \
    -H "Authorization: Bearer $ADMIN_TOKEN" 2>/dev/null \
    | jq -r '.[].id // empty' \
    | while read -r old_org_id; do
        [ -z "$old_org_id" ] && continue
        curl -s -o /dev/null -X DELETE \
          "$KEYCLOAK_URL/admin/realms/$REALM/organizations/$old_org_id/members/$ACTOR_USER_ID" \
          -H "Authorization: Bearer $ADMIN_TOKEN"
      done

  USER_REP=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$ACTOR_USER_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN")
  UPDATED_USER_REP=$(echo "$USER_REP" | jq \
    '.attributes.org_permissions = ["organization.owner"]
     | .requiredActions = []
     | .emailVerified = true')
  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$ACTOR_USER_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$UPDATED_USER_REP" >/dev/null

  ORG_NAME="${ORG_NAME:-frontend-org-${TEST_SUFFIX}}"
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
  if [ "$ORG_CREATE_HTTP" != "201" ] && [ "$ORG_CREATE_HTTP" != "200" ] && [ "$ORG_CREATE_HTTP" != "409" ]; then
    echo -e "${RED}✗ Failed to create frontend org${NC}"
    exit 1
  fi
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

  CREATE_MEMBER_RESP=$(curl -s -w "\n%{http_code}" -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/users" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"$MEMBER_USERNAME\",
      \"enabled\": true,
      \"emailVerified\": true,
      \"firstName\": \"Frontend\",
      \"lastName\": \"Member\",
      \"email\": \"$MEMBER_EMAIL\"
    }")
  CREATE_MEMBER_HTTP=$(echo "$CREATE_MEMBER_RESP" | tail -n1)
  if [ "$CREATE_MEMBER_HTTP" != "201" ] && [ "$CREATE_MEMBER_HTTP" != "409" ]; then
    echo -e "${RED}✗ Failed to create member user${NC}"
    exit 1
  fi
  MEMBER_USER_ID=$(lookup_user_id_by_username "$MEMBER_USERNAME")
  curl -s -o /dev/null -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/organizations/$ORG_ID/members" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "\"$MEMBER_USER_ID\""
}

login_actor() {
  TOKEN_RESP=$(curl -s -w "\n%{http_code}" -X POST \
    "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=$CLIENT_ID" \
    -d "username=$FRONTEND_USERNAME" \
    -d "password=$FRONTEND_PASSWORD" \
    -d "scope=organization email profile" \
    -d "grant_type=password")
  TOKEN_HTTP=$(echo "$TOKEN_RESP" | tail -n1)
  TOKEN_BODY=$(echo "$TOKEN_RESP" | sed '$d')
  AUTH_TOKEN=$(echo "$TOKEN_BODY" | jq -r '.access_token // empty')
  if [ "$TOKEN_HTTP" != "200" ] || [ -z "${AUTH_TOKEN:-}" ] || [ "$AUTH_TOKEN" = "null" ]; then
    echo -e "${RED}✗ Failed to login frontend actor${NC}"
    echo "$TOKEN_BODY"
    exit 1
  fi
}

bootstrap_project_if_needed() {
  PROJECT_ID=$(GANTRY_SERVER__CONFIG_FILE=gantry.toml \
    PYTHONPATH=src \
    DEBUG=false \
    UV_ENV_FILE=.env \
    ORG_ID="$ORG_ID" \
    ACTOR_USER_ID="$ACTOR_USER_ID" \
    BOOTSTRAP_PROJECT_NAME="frontend-bootstrap-$(date +%s)" \
    uv run python - <<'PY' | tail -n1
import asyncio
import os

from sqlalchemy import select

from gantry.db.factories import getSessionManager
from gantry.management.project.models import Project
from gantry.management.project.repositories import ProjectMemberRepository
from gantry.shared.utils.uuid_utils import uuid7


async def main():
    org_id = os.environ["ORG_ID"]
    actor_user_id = os.environ["ACTOR_USER_ID"]
    project_name = os.environ["BOOTSTRAP_PROJECT_NAME"]
    session_manager = getSessionManager()
    membership_repo = ProjectMemberRepository()

    async with session_manager.get_session() as session:
        existing_stmt = (
            select(Project)
            .join(
                membership_repo.model,
                membership_repo.model.project_id == Project.id,
            )
            .where(Project.organization_id == org_id)
            .where(membership_repo.model.user_id == actor_user_id)
            .order_by(Project.created_at.desc())
            .limit(1)
        )
        existing = await membership_repo.selectOne(session, existing_stmt)
        if existing is not None:
            print(existing.uuid)
            return

        project = Project(
            name=project_name,
            description="frontend bootstrap project",
            organization_id=org_id,
        )
        project.uuid = uuid7()
        session.add(project)
        await session.flush()
        await session.refresh(project)
        await membership_repo.upsertMembership(
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
    '["project.owner","projects.get_all","project.users.add","project.users.get_all","project.users.remove","project.users.permissions.read_write"]'
}

print_auth_context() {
  GANTRY_SERVER__CONFIG_FILE=gantry.toml \
  PYTHONPATH=src \
  AUTH_TOKEN="$AUTH_TOKEN" \
  AUTH_SERVER_URL="$KEYCLOAK_URL" \
  AUTH_REALM_NAME="$REALM" \
  AUTH_CLIENT_ID="$CLIENT_ID" \
  KEYCLOAK_SERVICE_CLIENT_ID="$SERVICE_CLIENT_ID" \
  KEYCLOAK_SERVICE_CLIENT_SECRET="$SERVICE_CLIENT_SECRET" \
  DEBUG=false \
  uv run python - <<'PY'
import asyncio
import base64
import json
import os

from gantry.management.auth.factories import getAuthService

token = os.environ["AUTH_TOKEN"]

payload = token.split(".")[1]
payload += "=" * (-len(payload) % 4)
claims = json.loads(base64.urlsafe_b64decode(payload.encode()))

auth_service = getAuthService()
user_info = asyncio.run(auth_service.verifyToken(token)).unwrap()
print(json.dumps({
    "token_claims_subset": {
        "org_id": claims.get("org_id"),
        "organization_id": claims.get("organization_id"),
        "organization": claims.get("organization"),
        "scope": claims.get("scope"),
    },
    "resolved_user_info": user_info,
}, indent=2))
PY
}

print_summary() {
  echo "===================================================="
  echo -e "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
  echo "===================================================="
  echo ""
  echo -e "${BLUE}Actor username:${NC} ${FRONTEND_USERNAME}"
  echo -e "${BLUE}Actor user id:${NC} ${ACTOR_USER_ID}"
  echo -e "${BLUE}Organization id:${NC} ${ORG_ID}"
  echo -e "${BLUE}Project id:${NC} ${PROJECT_ID}"
  echo -e "${BLUE}Member user id:${NC} ${MEMBER_USER_ID}"
  echo ""
}

print_header
preflight_checks
setup_frontend_actor
login_actor
bootstrap_project_if_needed

echo -e "${BLUE}Frontend login actor:${NC} ${FRONTEND_USERNAME}"
echo -e "${BLUE}Actor user id:${NC} ${ACTOR_USER_ID}"
echo -e "${BLUE}Organization id:${NC} ${ORG_ID}"
echo -e "${BLUE}Project id:${NC} ${PROJECT_ID}"
echo ""

echo -e "${CYAN}[INFO] Backend auth context resolved from frontend token${NC}"
print_auth_context
echo ""

run_test "Frontend login token can read org permission catalog" "200" \
  -X GET "$ORG_BASE_URL/permissions" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "Frontend login token can read project permission catalog" "200" \
  -X GET "$PROJECT_BASE_URL/permissions" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "Frontend login token can read organization metadata" "200" \
  -X GET "$ORG_BASE_URL/$ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "Frontend login token can read organization settings" "200" \
  -X GET "$ORG_BASE_URL/$ORG_ID/settings" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "Frontend login token can list organization users" "200" \
  -X GET "$ORG_BASE_URL/$ORG_ID/users" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "Frontend login token can read own organization permissions" "200" \
  -X GET "$ORG_BASE_URL/$ORG_ID/users/$ACTOR_USER_ID/permissions" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "Frontend login token can list joined projects" "200" \
  -X GET "$PROJECT_BASE_URL" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "Frontend login token can list org projects" "200" \
  -X GET "$PROJECT_BASE_URL?organization=$ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "Frontend login token can create a project" "201" \
  -X POST "$PROJECT_BASE_URL?organization=$ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"frontend-created-$(date +%s)\", \"description\": \"created from frontend smoke test\"}"

run_test "Frontend login token can list project users" "200" \
  -X GET "$PROJECT_BASE_URL/$PROJECT_ID/users" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "Frontend login token can read own project permissions" "200" \
  -X GET "$PROJECT_BASE_URL/$PROJECT_ID/users/$ACTOR_USER_ID/permissions" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "Frontend login token can add a member to project" "200 409" \
  -X POST "$PROJECT_BASE_URL/$PROJECT_ID/users" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"$MEMBER_USER_ID\"}"

run_test "Frontend login token can update member project permissions" "200" \
  -X PUT "$PROJECT_BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID/permissions" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"permissions":["project.users.get_all"]}'

run_test "Frontend login token can read member project permissions" "200" \
  -X GET "$PROJECT_BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID/permissions" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "Frontend login token can archive a project" "200" \
  -X POST "$PROJECT_BASE_URL/$PROJECT_ID/archive" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "Frontend login token can unarchive a project" "200" \
  -X POST "$PROJECT_BASE_URL/$PROJECT_ID/unarchive" \
  -H "Authorization: Bearer $AUTH_TOKEN"

print_summary

if [ "$FAIL" -ne 0 ]; then
  exit 1
fi
