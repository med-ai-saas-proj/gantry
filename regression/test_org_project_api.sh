#!/bin/bash
# Extended API scenario tests for:
# - Organization endpoints (validation and authz smoke cases)
# - Project endpoints
# - Project membership and project-scoped permissions
#
# Dependencies: curl, jq, uv (optional for --get-token mode)
#
# Optional env:
#   KEYCLOAK_URL (default: http://localhost:8080)
#   REALM (default: gantry)
#   CLIENT_ID (default: gantry-frontend)
#   KEYCLOAK_ADMIN_USERNAME (default: admin)
#   KEYCLOAK_ADMIN_PASSWORD (default: admin)
#   USE_CLEAN_TEST_ACTOR (default: 1)
#   CLEAN_ACTOR_USERNAME, CLEAN_ACTOR_PASSWORD, CLEAN_ACTOR_EMAIL
#   AUTH_TOKEN, ORG_ID (used when USE_CLEAN_TEST_ACTOR=0)
#   PROJECT_ID (if already known)
#   MEMBER_AUTH_TOKEN (if you already have another member token)
#   MEMBER_USER_ID (if you already have another member user id)

set -euo pipefail

ORG_BASE_URL="http://localhost:8000/management/v1/organizations"
PROJECT_BASE_URL="http://localhost:8000/management/v1/projects"

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-gantry}"
CLIENT_ID="${CLIENT_ID:-gantry-frontend}"
ADMIN_USERNAME="${KEYCLOAK_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
USE_CLEAN_TEST_ACTOR="${USE_CLEAN_TEST_ACTOR:-1}"

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

print_header() {
  echo "======================================================="
  echo "Org + Project + Project Permission Scenario Test Suite"
  echo "======================================================="
  echo ""
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

ensure_admin_token() {
  if [ -n "${ADMIN_TOKEN:-}" ] && [ "$ADMIN_TOKEN" != "null" ]; then
    return 0
  fi
  local attempt token_response
  for attempt in 1 2 3; do
    token_response=$(curl -sS --max-time 20 -X POST \
      "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "client_id=admin-cli" \
      -d "username=$ADMIN_USERNAME" \
      -d "password=$ADMIN_PASSWORD" \
      -d "grant_type=password" || true)
    ADMIN_TOKEN=$(echo "$token_response" | jq -r '.access_token // empty')
    if [ -n "${ADMIN_TOKEN:-}" ] && [ "$ADMIN_TOKEN" != "null" ]; then
      return 0
    fi
    sleep 1
  done
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
  local profile updated_profile
  profile=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/profile" \
    -H "Authorization: Bearer $ADMIN_TOKEN" 2>/dev/null || echo '{}')
  if echo "$profile" | jq -e \
    '.attributes[] | select(.name == "org_permissions")' \
    >/dev/null 2>&1; then
    return 0
  fi
  updated_profile=$(echo "$profile" | jq \
    '.attributes += [{
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

set_project_permissions_attr() {
  local user_id="$1"
  local project_id="$2"
  local permissions_json="$3"
  local attr_key="project_permissions"
  local user_rep updated_user
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
  updated_user=$(echo "$user_rep" | jq \
    --arg attr_key "$attr_key" \
    --argjson permissions "$combined" \
    '.attributes[$attr_key] = ($permissions | to_entries | map({(.key): .value} | tojson))')
  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$user_id" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$updated_user" >/dev/null
}

setup_clean_actor_and_org() {
  ensure_admin_token

  local realm_rep updated_realm suffix create_user_resp create_user_http
  local clean_org_name org_create_resp org_create_http user_rep updated_user
  local token_resp token_http token_body token
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

  suffix="$(date +%s)"
  CLEAN_ACTOR_USERNAME="${CLEAN_ACTOR_USERNAME:-org-project-clean-${suffix}}"
  CLEAN_ACTOR_PASSWORD="${CLEAN_ACTOR_PASSWORD:-Test123!${suffix}}"
  CLEAN_ACTOR_EMAIL="${CLEAN_ACTOR_EMAIL:-${CLEAN_ACTOR_USERNAME}@local.test}"

  create_user_resp=$(curl -s -w "\n%{http_code}" -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/users" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"$CLEAN_ACTOR_USERNAME\",
      \"enabled\": true,
      \"emailVerified\": true,
      \"firstName\": \"OrgProject\",
      \"lastName\": \"Actor\",
      \"email\": \"$CLEAN_ACTOR_EMAIL\"
    }")
  create_user_http=$(echo "$create_user_resp" | tail -n1)
  if [ "$create_user_http" != "201" ] && [ "$create_user_http" != "409" ]; then
    echo -e "${RED}✗ Failed to create clean actor (HTTP $create_user_http)${NC}"
    echo "  $(echo "$create_user_resp" | sed '$d')"
    exit 1
  fi

  ACTOR_USER_ID=$(lookup_user_id_by_username "$CLEAN_ACTOR_USERNAME")
  if [ -z "${ACTOR_USER_ID:-}" ]; then
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
      \"value\": \"$CLEAN_ACTOR_PASSWORD\"
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

  user_rep=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$ACTOR_USER_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN")
  updated_user=$(echo "$user_rep" | jq \
    '.attributes.org_permissions = ["organization.owner"]
     | .requiredActions = []
     | .emailVerified = true
     | .firstName = "OrgProject"
     | .lastName = "Actor"')
  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$ACTOR_USER_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$updated_user" >/dev/null

  if [ -z "${ORG_ID:-}" ]; then
    clean_org_name="${CLEAN_ORG_NAME:-org-project-clean-${suffix}}"
    org_create_resp=$(curl -s -w "\n%{http_code}" -X POST \
      "$KEYCLOAK_URL/admin/realms/$REALM/organizations" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"name\": \"$clean_org_name\",
        \"alias\": \"$clean_org_name\",
        \"enabled\": true
      }")
    org_create_http=$(echo "$org_create_resp" | tail -n1)
    if [ "$org_create_http" != "201" ] && [ "$org_create_http" != "200" ]; then
      echo -e "${RED}✗ Failed to create clean org (HTTP $org_create_http)${NC}"
      echo "  $(echo "$org_create_resp" | sed '$d')"
      exit 1
    fi
    ORG_ID=$(curl -sf \
      "$KEYCLOAK_URL/admin/realms/$REALM/organizations?search=$clean_org_name" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      | jq -r --arg org_name "$clean_org_name" \
        '.[] | select(.name == $org_name) | .id' \
      | head -n1)
  fi

  if [ -z "${ORG_ID:-}" ]; then
    echo -e "${RED}✗ Clean actor setup did not produce ORG_ID${NC}"
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
    -d "username=$CLEAN_ACTOR_USERNAME" \
    -d "password=$CLEAN_ACTOR_PASSWORD" \
    -d "scope=organization email profile" \
    -d "grant_type=password")
  token_http=$(echo "$token_resp" | tail -n1)
  token_body=$(echo "$token_resp" | sed '$d')
  token=$(echo "$token_body" | jq -r '.access_token // empty')
  if [ "$token_http" != "200" ] || [ -z "$token" ]; then
    echo -e "${RED}✗ Failed to get clean actor token (HTTP $token_http)${NC}"
    echo "  $token_body"
    exit 1
  fi

  AUTH_TOKEN="$token"
  export AUTH_TOKEN
  export ORG_ID
  export ACTOR_USER_ID
  echo -e "${GREEN}✓ Using clean actor ${CLEAN_ACTOR_USERNAME} in org ${ORG_ID}${NC}"
}

get_actor_user_id() {
  AUTH_TOKEN="$AUTH_TOKEN" uv run python - <<'PY'
import os, json, base64
t = os.environ.get("AUTH_TOKEN","")
parts = t.split(".")
if len(parts) < 2:
    print("")
    raise SystemExit(0)
p = parts[1] + ("=" * (-len(parts[1]) % 4))
try:
    print(json.loads(base64.urlsafe_b64decode(p.encode())).get("sub",""))
except Exception:
    print("")
PY
}

create_or_get_member_user() {
  ensure_admin_token
  if [ -n "${MEMBER_USER_ID:-}" ] && [ "$MEMBER_USER_ID" != "null" ]; then
    return 0
  fi

  local suffix
  suffix="$(date +%s)"
  MEMBER_USERNAME="${MEMBER_USERNAME:-proj-member-${suffix}}"
  MEMBER_PASSWORD="${MEMBER_PASSWORD:-Test123!${suffix}}"
  MEMBER_EMAIL="${MEMBER_EMAIL:-${MEMBER_USERNAME}@local.test}"

  local create_resp create_http
  create_resp=$(curl -s -w "\n%{http_code}" -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/users" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"$MEMBER_USERNAME\",
      \"enabled\": true,
      \"emailVerified\": true,
      \"email\": \"$MEMBER_EMAIL\",
      \"firstName\": \"Project\",
      \"lastName\": \"Member\"
    }")
  create_http=$(echo "$create_resp" | tail -n1)
  if [ "$create_http" != "201" ] && [ "$create_http" != "409" ]; then
    echo -e "${RED}✗ Failed to create/reuse member user (HTTP $create_http)${NC}"
    echo "  $(echo "$create_resp" | sed '$d')"
    exit 1
  fi

  MEMBER_USER_ID=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users?username=$MEMBER_USERNAME" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r --arg username "$MEMBER_USERNAME" '.[] | select(.username == $username) | .id' | head -n1)
  if [ -z "${MEMBER_USER_ID:-}" ]; then
    echo -e "${RED}✗ Could not resolve member user id${NC}"
    exit 1
  fi

  local pass_resp pass_http
  pass_resp=$(curl -s -w "\n%{http_code}" -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$MEMBER_USER_ID/reset-password" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"type\": \"password\",
      \"temporary\": false,
      \"value\": \"$MEMBER_PASSWORD\"
    }")
  pass_http=$(echo "$pass_resp" | tail -n1)
  if [ "$pass_http" != "200" ] && [ "$pass_http" != "204" ]; then
    echo -e "${RED}✗ Failed setting member password (HTTP $pass_http)${NC}"
    exit 1
  fi

  # Make sure member belongs to this org for add-user-to-project scenarios.
  local add_resp add_http
  add_resp=$(curl -s -w "\n%{http_code}" -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/organizations/$ORG_ID/members" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "\"$MEMBER_USER_ID\"")
  add_http=$(echo "$add_resp" | tail -n1)
  if [ "$add_http" != "201" ] && [ "$add_http" != "409" ]; then
    echo -e "${YELLOW}⚠ Could not add member user into org (HTTP $add_http)${NC}"
  fi

  if [ -z "${MEMBER_AUTH_TOKEN:-}" ]; then
    token_resp=$(curl -s -w "\n%{http_code}" -X POST \
      "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "client_id=$CLIENT_ID" \
      -d "username=$MEMBER_USERNAME" \
      -d "password=$MEMBER_PASSWORD" \
      -d "scope=organization email profile" \
      -d "grant_type=password")
    token_http=$(echo "$token_resp" | tail -n1)
    token_body=$(echo "$token_resp" | sed '$d')
    token=$(echo "$token_body" | jq -r '.access_token // empty')
    if [ "$token_http" = "200" ] && [ -n "$token" ]; then
      MEMBER_AUTH_TOKEN="$token"
    fi
  fi
}

bootstrap_project_if_needed() {
  if [ -n "${PROJECT_ID:-}" ] && [ "${PROJECT_ID}" != "none" ]; then
    return 0
  fi
  if [ -z "${ACTOR_USER_ID:-}" ]; then
    echo -e "${YELLOW}⚠ Skipping bootstrap project setup because actor user id is unavailable${NC}"
    return 0
  fi

  local bootstrap_name
  bootstrap_name="${BOOTSTRAP_PROJECT_NAME:-bootstrap-project-$(date +%s)}"

  PROJECT_ID=$(PYTHONPATH=. \
    DEBUG=1 \
    UV_ENV_FILE=.env \
    ORG_ID="$ORG_ID" \
    ACTOR_USER_ID="$ACTOR_USER_ID" \
    BOOTSTRAP_PROJECT_NAME="$bootstrap_name" \
    uv run python - <<'PY' | tail -n1
import asyncio
import os

from gantry.db.factories import getSessionManager
from gantry.management.project.models import Project
from gantry.management.project.repositories import (
    ProjectMemberRepository,
    ProjectRepository,
)
from gantry.shared.utils.uuid_utils import uuid7
from sqlalchemy import select


async def main():
    org_id = os.environ["ORG_ID"]
    actor_user_id = os.environ["ACTOR_USER_ID"]
    project_name = os.environ["BOOTSTRAP_PROJECT_NAME"]
    session_manager = getSessionManager()
    project_repo = ProjectRepository()
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
        existing = await project_repo.selectOne(session, existing_stmt)
        if existing is not None:
            print(existing.uuid)
            return

        project = Project(
            name=project_name,
            description="bootstrap project for project permission scenarios",
            organization_id=org_id,
        )
        project.uuid = uuid7()
        await project_repo.add(session, project)
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

  if [ -n "${PROJECT_ID:-}" ]; then
    set_project_permissions_attr \
      "$ACTOR_USER_ID" \
      "$PROJECT_ID" \
      '["project.owner","projects.get_all"]'
    echo -e "${GREEN}✓ Bootstrapped project for advanced scenarios: ${PROJECT_ID}${NC}"
  else
    echo -e "${YELLOW}⚠ Bootstrap project setup did not produce a project id${NC}"
  fi
}

try_get_token() {
  if [ "${1:-}" != "--get-token" ]; then
    return 0
  fi
  if [ -z "${KEYCLOAK_USERNAME:-}" ] || [ -z "${KEYCLOAK_PASSWORD:-}" ]; then
    echo -e "${YELLOW}Set KEYCLOAK_USERNAME and KEYCLOAK_PASSWORD for --get-token${NC}"
    exit 1
  fi
  token_resp=$(curl -s -w "\n%{http_code}" -X POST \
    "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=$CLIENT_ID" \
    -d "username=$KEYCLOAK_USERNAME" \
    -d "password=$KEYCLOAK_PASSWORD" \
    -d "scope=organization email profile" \
    -d "grant_type=password")
  token_http=$(echo "$token_resp" | tail -n1)
  token_body=$(echo "$token_resp" | sed '$d')
  token=$(echo "$token_body" | jq -r '.access_token // empty')
  if [ "$token_http" != "200" ] || [ -z "$token" ]; then
    echo -e "${RED}✗ Failed to get token (HTTP $token_http)${NC}"
    echo "  $token_body"
    exit 1
  fi
  AUTH_TOKEN="$token"
  export AUTH_TOKEN
  echo -e "${GREEN}✓ Got AUTH_TOKEN via --get-token${NC}"
  echo ""
}

resolve_existing_project_id() {
  if [ -n "${PROJECT_ID:-}" ]; then
    return 0
  fi

  run_test "GET my joined projects to discover a project id" "200" \
    -X GET "$PROJECT_BASE_URL" \
    -H "Authorization: Bearer $AUTH_TOKEN"
  PROJECT_ID=$(echo "$RESPONSE_BODY" | jq -r '.results[0].project_uuid // empty' 2>/dev/null || true)
}

print_header
if [ "$USE_CLEAN_TEST_ACTOR" = "1" ]; then
  setup_clean_actor_and_org
else
  try_get_token "${1:-}"
fi

AUTH_TOKEN="${AUTH_TOKEN:-}"
ORG_ID="${ORG_ID:-}"

if [ -z "$AUTH_TOKEN" ]; then
  echo -e "${RED}AUTH_TOKEN is required${NC}"
  exit 1
fi
if [ -z "$ORG_ID" ]; then
  echo -e "${RED}ORG_ID is required${NC}"
  exit 1
fi

ACTOR_USER_ID="${ACTOR_USER_ID:-$(get_actor_user_id)}"
if [ -z "${ACTOR_USER_ID:-}" ]; then
  echo -e "${YELLOW}⚠ Could not decode actor user id from AUTH_TOKEN${NC}"
fi

echo -e "${BLUE}ORG_ID=${ORG_ID}${NC}"
echo -e "${BLUE}ACTOR_USER_ID=${ACTOR_USER_ID:-unknown}${NC}"
echo ""

# ------------------------------------------------------------
# Organization scenarios (unit-style API scenarios)
# ------------------------------------------------------------
run_test "ORG: GET settings" "200" \
  -X GET "$ORG_BASE_URL/$ORG_ID/settings" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "ORG: GET permission catalog" "200" \
  -X GET "$ORG_BASE_URL/permissions" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "ORG: PATCH settings extra jsonb object" "200" \
  -X PATCH "$ORG_BASE_URL/$ORG_ID/settings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"rate_limit": 77, "extra": {"features": {"project": true}, "tags": ["a","b"]}}'

run_test "ORG: PATCH settings invalid extra type array -> 400/422" "400 422" \
  -X PATCH "$ORG_BASE_URL/$ORG_ID/settings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"rate_limit": 77, "extra": ["bad"]}'

run_test "ORG: GET users pagination" "200" \
  -X GET "$ORG_BASE_URL/$ORG_ID/users?limit=20&offset=0" \
  -H "Authorization: Bearer $AUTH_TOKEN"

if [ -n "${ACTOR_USER_ID:-}" ]; then
  run_test "ORG: GET own org permissions (self-read)" "200" \
    -X GET "$ORG_BASE_URL/$ORG_ID/users/$ACTOR_USER_ID/permissions" \
    -H "Authorization: Bearer $AUTH_TOKEN"
fi

# ------------------------------------------------------------
# Project scenarios (permissions and behavior)
# ------------------------------------------------------------
run_test "PROJECT: GET joined projects (no permission required)" "200" \
  -X GET "$PROJECT_BASE_URL" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "PROJECT: GET permission catalog" "200" \
  -X GET "$PROJECT_BASE_URL/permissions" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "PROJECT: GET org-wide projects (requires projects.get_all)" "200 403" \
  -X GET "$PROJECT_BASE_URL?organization=$ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "PROJECT: POST create project missing organization query -> 400/422" "400 422" \
  -X POST "$PROJECT_BASE_URL" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"missing-org-query"}'

run_test "PROJECT: POST create project invalid name empty -> 400/422" "400 422" \
  -X POST "$PROJECT_BASE_URL?organization=$ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"","description":"invalid"}'

run_test "PROJECT: POST create project valid body (201 for org owner/bootstrap actor)" "201" \
  -X POST "$PROJECT_BASE_URL?organization=$ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"proj-$(date +%s)\",\"description\":\"created by scenario test\"}"

if [ "$HTTP_CODE" = "201" ]; then
  PROJECT_ID=$(echo "$RESPONSE_BODY" | jq -r '.project_uuid // empty')
fi

resolve_existing_project_id
bootstrap_project_if_needed
echo -e "${BLUE}PROJECT_ID=${PROJECT_ID:-none}${NC}"
echo ""

if [ -z "${PROJECT_ID:-}" ]; then
  echo -e "${YELLOW}[SKIP] No project available. Advanced project permission scenarios skipped.${NC}"
  echo -e "${YELLOW}       This indicates missing bootstrap permission path for first project creation.${NC}"
  echo ""
else
  create_or_get_member_user
  echo -e "${BLUE}MEMBER_USER_ID=${MEMBER_USER_ID:-unknown}${NC}"
  echo ""

  run_test "PROJECT: GET settings" "200" \
    -X GET "$PROJECT_BASE_URL/$PROJECT_ID/settings" \
    -H "Authorization: Bearer $AUTH_TOKEN"

  run_test "PROJECT: PATCH settings valid body" "200" \
    -X PATCH "$PROJECT_BASE_URL/$PROJECT_ID/settings" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"rate_limit": 150, "extra": {"routing": {"mode": "fast"}}}'

  run_test "PROJECT: PATCH settings invalid rate_limit -> 400/422" "400 422" \
    -X PATCH "$PROJECT_BASE_URL/$PROJECT_ID/settings" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"rate_limit": -1, "extra": {"routing": "bad"}}'

  run_test "PROJECT: GET project users list (requires project.users.get_all)" "200 403" \
    -X GET "$PROJECT_BASE_URL/$PROJECT_ID/users?limit=20&offset=0" \
    -H "Authorization: Bearer $AUTH_TOKEN"

  if [ -n "${ACTOR_USER_ID:-}" ]; then
    run_test "PROJECT: GET actor own project permissions (self-read allowed)" "200" \
      -X GET "$PROJECT_BASE_URL/$PROJECT_ID/users/$ACTOR_USER_ID/permissions" \
      -H "Authorization: Bearer $AUTH_TOKEN"
  fi

  run_test "PROJECT: POST add member user to project" "200 403 409" \
    -X POST "$PROJECT_BASE_URL/$PROJECT_ID/users" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"$MEMBER_USER_ID\"}"

  run_test "PROJECT: PUT member permissions invalid permission -> 400" "400 403" \
    -X PUT "$PROJECT_BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID/permissions" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"permissions":["project.users.get_all","bogus.permission"]}'

  run_test "PROJECT: PUT member permissions valid minimal set" "200 403 404" \
    -X PUT "$PROJECT_BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID/permissions" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"permissions":["project.settings.read"]}'

  run_test "PROJECT: GET member permissions" "200 403 404" \
    -X GET "$PROJECT_BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID/permissions" \
    -H "Authorization: Bearer $AUTH_TOKEN"

  if [ "$HTTP_CODE" = "200" ] && [ -n "${MEMBER_AUTH_TOKEN:-}" ]; then
    run_test "PROJECT MEMBER: self-read granted permission should pass" "200" \
      -X GET "$PROJECT_BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID/permissions" \
      -H "Authorization: Bearer $MEMBER_AUTH_TOKEN"
  fi

  run_test "PROJECT: Revoke member permissions to empty set" "200 403 404" \
    -X PUT "$PROJECT_BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID/permissions" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"permissions":[]}'

  run_test "PROJECT: GET member permissions after revoke" "200 403 404" \
    -X GET "$PROJECT_BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID/permissions" \
    -H "Authorization: Bearer $AUTH_TOKEN"

  run_test "PROJECT: Archive project (owner only)" "200 403" \
    -X POST "$PROJECT_BASE_URL/$PROJECT_ID/archive" \
    -H "Authorization: Bearer $AUTH_TOKEN"

  run_test "PROJECT: Unarchive project (owner only)" "200 403" \
    -X POST "$PROJECT_BASE_URL/$PROJECT_ID/unarchive" \
    -H "Authorization: Bearer $AUTH_TOKEN"

  if [ -n "${ACTOR_USER_ID:-}" ]; then
    run_test "PROJECT: Remove last owner should fail 403" "403" \
      -X DELETE "$PROJECT_BASE_URL/$PROJECT_ID/users/$ACTOR_USER_ID" \
      -H "Authorization: Bearer $AUTH_TOKEN"
  fi

  run_test "PROJECT: Remove member from project" "200 403 404" \
    -X DELETE "$PROJECT_BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID" \
    -H "Authorization: Bearer $AUTH_TOKEN"

  run_test "PROJECT: Remove same member again should 404/403" "403 404" \
    -X DELETE "$PROJECT_BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID" \
    -H "Authorization: Bearer $AUTH_TOKEN"

  run_test "PROJECT: Unauthenticated access should fail 401/403" "401 403" \
    -X GET "$PROJECT_BASE_URL/$PROJECT_ID/users"

  # Cross-project permission isolation scenario
  if [ -n "${ACTOR_USER_ID:-}" ]; then
    run_test "PROJECT: Create project B as org owner" "201" \
      -X POST "$PROJECT_BASE_URL?organization=$ORG_ID" \
      -H "Authorization: Bearer $AUTH_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"proj-b-$(date +%s)\",\"description\":\"project B for isolation\"}"

    if [ "$HTTP_CODE" = "201" ]; then
      PROJECT_B_ID=$(echo "$RESPONSE_BODY" | jq -r '.project_uuid // empty')
      if [ -n "${PROJECT_B_ID:-}" ]; then
        run_test "PROJECT: Add member user to project B" "200 409" \
          -X POST "$PROJECT_BASE_URL/$PROJECT_B_ID/users" \
          -H "Authorization: Bearer $AUTH_TOKEN" \
          -H "Content-Type: application/json" \
          -d "{\"user_id\":\"$MEMBER_USER_ID\"}"

        run_test "PROJECT: Set member permission in project B to users.get_all" "200 403 404" \
          -X PUT "$PROJECT_BASE_URL/$PROJECT_B_ID/users/$MEMBER_USER_ID/permissions" \
          -H "Authorization: Bearer $AUTH_TOKEN" \
          -H "Content-Type: application/json" \
          -d '{"permissions":["project.users.get_all"]}'

          # Read permissions from project A and B and compare. They should differ.
          PERM_A=$(curl -s -X GET \
            "$PROJECT_BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID/permissions" \
            -H "Authorization: Bearer $AUTH_TOKEN" | jq -c '.permissions // []' 2>/dev/null || echo "[]")
          PERM_B=$(curl -s -X GET \
            "$PROJECT_BASE_URL/$PROJECT_B_ID/users/$MEMBER_USER_ID/permissions" \
            -H "Authorization: Bearer $AUTH_TOKEN" | jq -c '.permissions // []' 2>/dev/null || echo "[]")

          TEST_NUM=$((TEST_NUM + 1))
          echo -e "${CYAN}[TEST $TEST_NUM] PROJECT: Cross-project permission isolation A != B${NC}"
          echo "  project A perms: $PERM_A"
          echo "  project B perms: $PERM_B"
          if [ "$PERM_A" != "$PERM_B" ]; then
            echo -e "  ${GREEN}✓ PASS (member has different permissions across projects)${NC}"
            PASS=$((PASS + 1))
          else
            echo -e "  ${RED}✗ FAIL (permissions unexpectedly identical)${NC}"
            FAIL=$((FAIL + 1))
          fi
          echo ""
      fi
    fi
  fi

  if [ -n "${MEMBER_AUTH_TOKEN:-}" ] && [ -n "${MEMBER_USER_ID:-}" ]; then
    run_test "PROJECT MEMBER: self-read own permission should pass" "200 404" \
      -X GET "$PROJECT_BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID/permissions" \
      -H "Authorization: Bearer $MEMBER_AUTH_TOKEN"

    if [ -n "${ACTOR_USER_ID:-}" ]; then
      run_test "PROJECT MEMBER: read other user permission should fail 403/404" "403 404" \
        -X GET "$PROJECT_BASE_URL/$PROJECT_ID/users/$ACTOR_USER_ID/permissions" \
        -H "Authorization: Bearer $MEMBER_AUTH_TOKEN"
    fi

    run_test "PROJECT MEMBER: archive project should fail 403/404" "403 404" \
      -X POST "$PROJECT_BASE_URL/$PROJECT_ID/archive" \
      -H "Authorization: Bearer $MEMBER_AUTH_TOKEN"
  fi
fi

echo "=========================================="
echo -e "Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC} (out of $TEST_NUM)"
echo "=========================================="

exit $FAIL
