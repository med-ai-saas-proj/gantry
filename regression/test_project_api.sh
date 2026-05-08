#!/bin/bash
# Test script for Project API endpoints
# Style aligned with scripts/test_organization_api.sh
#
# Dependencies: curl, jq, uv (optional for --get-token)
#
# Required:
#   AUTH_TOKEN
#   ORG_ID
#
# Optional:
#   USE_CLEAN_TEST_ACTOR=1 (default)
#   PROJECT_ID
#   KEYCLOAK_URL, REALM, CLIENT_ID
#   KEYCLOAK_ADMIN_USERNAME, KEYCLOAK_ADMIN_PASSWORD
#   MEMBER_USER_ID, MEMBER_AUTH_TOKEN

set -euo pipefail

BASE_URL="http://localhost:8000/management/v1/projects"
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
  KEYCLOAK_USERNAME="${KEYCLOAK_USERNAME:-project-api-test-${TEST_USER_SUFFIX}}"
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
      \"firstName\": \"Project\",
      \"lastName\": \"Tester\",
      \"email\": \"$TEST_EMAIL\"
    }")
  CREATE_USER_HTTP=$(echo "$CREATE_USER_RESP" | tail -n1)
  if [ "$CREATE_USER_HTTP" != "201" ] && [ "$CREATE_USER_HTTP" != "409" ]; then
    echo -e "${RED}✗ Failed to create clean actor (HTTP $CREATE_USER_HTTP)${NC}"
    exit 1
  fi

  ACTOR_USER_ID=$(lookup_user_id_by_username "$KEYCLOAK_USERNAME")
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
      \"value\": \"$KEYCLOAK_PASSWORD\"
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
     | .emailVerified = true
     | .firstName = "Project"
     | .lastName = "Tester"')
  curl -sf -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$ACTOR_USER_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$UPDATED_USER_REP" >/dev/null

  if [ -z "${ORG_ID:-}" ]; then
    ORG_NAME="project-api-org-$(date +%s%N)"
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
    -d "\"$ACTOR_USER_ID\""

  TOKEN_RESP=$(curl -s -w "\n%{http_code}" -X POST \
    "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=$CLIENT_ID" \
    -d "username=$KEYCLOAK_USERNAME" \
    -d "password=$KEYCLOAK_PASSWORD" \
    -d "scope=organization email profile" \
    -d "grant_type=password")
  TOKEN_HTTP=$(echo "$TOKEN_RESP" | tail -n1)
  TOKEN_BODY=$(echo "$TOKEN_RESP" | sed '$d')
  AUTH_TOKEN=$(echo "$TOKEN_BODY" | jq -r '.access_token // empty')
  if [ "$TOKEN_HTTP" != "200" ] || [ -z "${AUTH_TOKEN:-}" ]; then
    echo -e "${RED}✗ Failed to get clean actor token${NC}"
    exit 1
  fi
  export AUTH_TOKEN ORG_ID ACTOR_USER_ID
}

bootstrap_project_if_needed() {
  if [ -n "${PROJECT_ID:-}" ] && [ "${PROJECT_ID}" != "none" ]; then
    return 0
  fi
  PROJECT_ID=$(PYTHONPATH=. \
    DEBUG=1 \
    UV_ENV_FILE=.env \
    ORG_ID="$ORG_ID" \
    ACTOR_USER_ID="$ACTOR_USER_ID" \
    BOOTSTRAP_PROJECT_NAME="project-api-bootstrap-$(date +%s)" \
    uv run python - <<'PY' | tail -n1
import asyncio
import os

from gantry.db.factories import getSessionManager
from gantry.management.project.models import Project
from gantry.management.project.repositories import ProjectMemberRepository
from gantry.shared.utils.uuid_utils import uuid7
from sqlalchemy import select


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
            description="bootstrap project for project api test",
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
    '["project.owner","projects.get_all"]'
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
  MEMBER_USERNAME="${MEMBER_USERNAME:-project-test-member-${suffix}}"
  MEMBER_PASSWORD="${MEMBER_PASSWORD:-Test123!${suffix}}"
  MEMBER_EMAIL="${MEMBER_EMAIL:-${MEMBER_USERNAME}@local.test}"

  CREATE_USER_RESP=$(curl -s -w "\n%{http_code}" -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/users" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"$MEMBER_USERNAME\",
      \"enabled\": true,
      \"emailVerified\": true,
      \"email\": \"$MEMBER_EMAIL\"
    }")
  CREATE_USER_HTTP=$(echo "$CREATE_USER_RESP" | tail -n1)
  if [ "$CREATE_USER_HTTP" != "201" ] && [ "$CREATE_USER_HTTP" != "409" ]; then
    echo -e "${RED}✗ Failed to create/reuse member user (HTTP $CREATE_USER_HTTP)${NC}"
    exit 1
  fi

  MEMBER_USER_ID=$(curl -sf \
    "$KEYCLOAK_URL/admin/realms/$REALM/users?username=$MEMBER_USERNAME&exact=true" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0].id // empty')
  if [ -z "${MEMBER_USER_ID:-}" ]; then
    echo -e "${RED}✗ Could not resolve member user id${NC}"
    exit 1
  fi

  curl -s -o /dev/null -X PUT \
    "$KEYCLOAK_URL/admin/realms/$REALM/users/$MEMBER_USER_ID/reset-password" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"type\": \"password\",
      \"temporary\": false,
      \"value\": \"$MEMBER_PASSWORD\"
    }"

  # ensure member in org for add-user tests
  ADD_MEMBER_RESP=$(curl -s -w "\n%{http_code}" -X POST \
    "$KEYCLOAK_URL/admin/realms/$REALM/organizations/$ORG_ID/members" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "\"$MEMBER_USER_ID\"")
  ADD_MEMBER_HTTP=$(echo "$ADD_MEMBER_RESP" | tail -n1)
  if [ "$ADD_MEMBER_HTTP" != "201" ] && [ "$ADD_MEMBER_HTTP" != "409" ]; then
    echo -e "${YELLOW}⚠ Adding member to org returned HTTP $ADD_MEMBER_HTTP${NC}"
  fi

  if [ -z "${MEMBER_AUTH_TOKEN:-}" ]; then
    TOKEN_RESP=$(curl -s -w "\n%{http_code}" -X POST \
      "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "client_id=$CLIENT_ID" \
      -d "username=$MEMBER_USERNAME" \
      -d "password=$MEMBER_PASSWORD" \
      -d "scope=organization email profile" \
      -d "grant_type=password")
    TOKEN_HTTP=$(echo "$TOKEN_RESP" | tail -n1)
    TOKEN_BODY=$(echo "$TOKEN_RESP" | sed '$d')
    TOKEN=$(echo "$TOKEN_BODY" | jq -r '.access_token // empty')
    if [ "$TOKEN_HTTP" = "200" ] && [ -n "$TOKEN" ]; then
      MEMBER_AUTH_TOKEN="$TOKEN"
    fi
  fi
}

if [ "${1:-}" = "--get-token" ]; then
  if [ -z "${KEYCLOAK_USERNAME:-}" ] || [ -z "${KEYCLOAK_PASSWORD:-}" ]; then
    echo -e "${YELLOW}Set KEYCLOAK_USERNAME and KEYCLOAK_PASSWORD for --get-token${NC}"
    exit 1
  fi
  TOKEN_RESP=$(curl -s -w "\n%{http_code}" -X POST \
    "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=$CLIENT_ID" \
    -d "username=$KEYCLOAK_USERNAME" \
    -d "password=$KEYCLOAK_PASSWORD" \
    -d "scope=organization email profile" \
    -d "grant_type=password")
  TOKEN_HTTP=$(echo "$TOKEN_RESP" | tail -n1)
  TOKEN_BODY=$(echo "$TOKEN_RESP" | sed '$d')
  AUTH_TOKEN=$(echo "$TOKEN_BODY" | jq -r '.access_token // empty')
  if [ "$TOKEN_HTTP" != "200" ] || [ -z "${AUTH_TOKEN:-}" ]; then
    echo -e "${RED}✗ Failed to get token${NC}"
    echo "  $TOKEN_BODY"
    exit 1
  fi
fi

AUTH_TOKEN="${AUTH_TOKEN:-}"
ORG_ID="${ORG_ID:-}"

if [ "$USE_CLEAN_TEST_ACTOR" = "1" ]; then
  setup_clean_actor_and_org
  AUTH_TOKEN="${AUTH_TOKEN:-}"
  ORG_ID="${ORG_ID:-}"
fi

echo "=========================================="
echo "Testing Project API Endpoints"
echo "=========================================="
echo ""

if [ -z "$AUTH_TOKEN" ]; then
  echo -e "${RED}AUTH_TOKEN is required${NC}"
  exit 1
fi
if [ -z "$ORG_ID" ]; then
  echo -e "${RED}ORG_ID is required${NC}"
  exit 1
fi

ACTOR_USER_ID=$(get_actor_user_id)
ACTOR_USER_ID="${ACTOR_USER_ID:-$(get_actor_user_id)}"
echo -e "${BLUE}ORG_ID=$ORG_ID${NC}"
echo -e "${BLUE}ACTOR_USER_ID=${ACTOR_USER_ID:-unknown}${NC}"
echo ""

run_test "GET my joined projects" "200" \
  -X GET "$BASE_URL" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "GET project permission catalog" "200" \
  -X GET "$BASE_URL/permissions" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "GET org projects (requires projects.get_all)" "200 403" \
  -X GET "$BASE_URL?organization=$ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN"

run_test "POST create project missing organization query (should fail 400/422)" "400 422" \
  -X POST "$BASE_URL" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"missing-org"}'

run_test "POST create project invalid name (should fail 400/422)" "400 422" \
  -X POST "$BASE_URL?organization=$ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"","description":"invalid"}'

run_test "POST create project valid body (201 for org owner/bootstrap actor)" "201" \
  -X POST "$BASE_URL?organization=$ORG_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"project-api-test-$(date +%s)\",\"description\":\"test\"}"

if [ "$HTTP_CODE" = "201" ]; then
  PROJECT_ID=$(echo "$RESPONSE_BODY" | jq -r '.project_uuid // empty')
fi

if [ -n "${PROJECT_ID:-}" ]; then
  run_test "PUT update project metadata" "200" \
    -X PUT "$BASE_URL/$PROJECT_ID" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"project-api-renamed","description":"updated by shell test"}'
fi

if [ -z "${PROJECT_ID:-}" ]; then
  RESP=$(curl -s -X GET "$BASE_URL" -H "Authorization: Bearer $AUTH_TOKEN")
  PROJECT_ID=$(echo "$RESP" | jq -r '.results[0].project_uuid // empty' 2>/dev/null || true)
fi

bootstrap_project_if_needed

if [ -z "${PROJECT_ID:-}" ]; then
  echo -e "${YELLOW}[SKIP] No project available for project-id scenarios${NC}"
  echo ""
else
  run_test "GET project settings" "200" \
    -X GET "$BASE_URL/$PROJECT_ID/settings" \
    -H "Authorization: Bearer $AUTH_TOKEN"

  run_test "PATCH project settings valid body" "200" \
    -X PATCH "$BASE_URL/$PROJECT_ID/settings" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"rate_limit":150,"extra":{"routing":{"mode":"fast"}}}'

  run_test "PATCH project settings invalid rate_limit (should fail 400/422)" "400 422" \
    -X PATCH "$BASE_URL/$PROJECT_ID/settings" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"rate_limit":-1,"extra":{"routing":"bad"}}'

  create_or_get_member_user

  run_test "GET project users" "200 403" \
    -X GET "$BASE_URL/$PROJECT_ID/users?limit=20&offset=0" \
    -H "Authorization: Bearer $AUTH_TOKEN"

  if [ -n "${ACTOR_USER_ID:-}" ]; then
    run_test "GET actor own project permissions (self-read)" "200" \
      -X GET "$BASE_URL/$PROJECT_ID/users/$ACTOR_USER_ID/permissions" \
      -H "Authorization: Bearer $AUTH_TOKEN"
  fi

  run_test "POST add user to project" "200 403 409" \
    -X POST "$BASE_URL/$PROJECT_ID/users" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"$MEMBER_USER_ID\"}"

  run_test "PUT user permissions invalid permission (should fail 400/403)" "400 403" \
    -X PUT "$BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID/permissions" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"permissions":["project.users.get_all","invalid.permission"]}'

  run_test "GET member permissions" "200 403 404" \
    -X GET "$BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID/permissions" \
    -H "Authorization: Bearer $AUTH_TOKEN"

  if [ "$HTTP_CODE" = "200" ] && [ -n "${MEMBER_AUTH_TOKEN:-}" ]; then
    run_test "MEMBER self-read after actor permission update" "200" \
      -X GET "$BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID/permissions" \
      -H "Authorization: Bearer $MEMBER_AUTH_TOKEN"
  fi

  run_test "PUT member permissions revoke to empty set" "200 403 404" \
    -X PUT "$BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID/permissions" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"permissions":[]}'

  run_test "GET member permissions after revoke" "200 403 404" \
    -X GET "$BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID/permissions" \
    -H "Authorization: Bearer $AUTH_TOKEN"

  run_test "POST archive project (owner only)" "200 403 409" \
    -X POST "$BASE_URL/$PROJECT_ID/archive" \
    -H "Authorization: Bearer $AUTH_TOKEN"

  run_test "POST unarchive project (owner only)" "200 403" \
    -X POST "$BASE_URL/$PROJECT_ID/unarchive" \
    -H "Authorization: Bearer $AUTH_TOKEN"

  run_test "DELETE member from project (or 409 if project already archived)" "200 403 404 409" \
    -X DELETE "$BASE_URL/$PROJECT_ID/users/$MEMBER_USER_ID" \
    -H "Authorization: Bearer $AUTH_TOKEN"

  run_test "GET project users without auth (should fail 401/403)" "401 403" \
    -X GET "$BASE_URL/$PROJECT_ID/users"

  if [ -n "${MEMBER_AUTH_TOKEN:-}" ] && [ -n "${ACTOR_USER_ID:-}" ]; then
    run_test "MEMBER token: read actor permission should fail 403/404" "403 404" \
      -X GET "$BASE_URL/$PROJECT_ID/users/$ACTOR_USER_ID/permissions" \
      -H "Authorization: Bearer $MEMBER_AUTH_TOKEN"
  fi
fi

echo "=========================================="
echo -e "Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC} (out of $TEST_NUM)"
echo "=========================================="

exit $FAIL
