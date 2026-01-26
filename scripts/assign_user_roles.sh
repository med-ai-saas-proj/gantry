#!/bin/bash
# Assign client-specific roles to a user in Keycloak

set -e

# Configuration
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-dev}"
CLIENT_ID="${CLIENT_ID:-med-ai-saas-app}"
ADMIN_USERNAME="${KEYCLOAK_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"

USER_EMAIL="$1"
shift
ROLES_TO_ASSIGN=("$@")

# Usage
if [ -z "$USER_EMAIL" ] || [ ${#ROLES_TO_ASSIGN[@]} -eq 0 ]; then
    cat << EOF
Usage: $0 <user-email> <role1> [role2] ...

Examples:
  $0 user@example.com member.add member.edit
  $0 user@example.com super_admin

Common roles:
  super_admin
  member.admin, member.add, member.edit, member.delete, member.view
  permission.admin, apikey.admin, user.admin, audit.view, settings.admin
EOF
    exit 1
fi

echo "Assigning roles to: $USER_EMAIL"
echo "Roles: ${ROLES_TO_ASSIGN[*]}"

# Get admin token
ADMIN_TOKEN=$(curl -sf -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=admin-cli" \
  -d "username=$ADMIN_USERNAME" \
  -d "password=$ADMIN_PASSWORD" \
  -d "grant_type=password" | jq -r '.access_token')

if [ -z "$ADMIN_TOKEN" ] || [ "$ADMIN_TOKEN" = "null" ]; then
    echo "Error: Failed to authenticate"
    exit 1
fi

# Get client UUID
CLIENT_UUID=$(curl -sf "$KEYCLOAK_URL/admin/realms/$REALM/clients?clientId=$CLIENT_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0].id')

if [ -z "$CLIENT_UUID" ] || [ "$CLIENT_UUID" = "null" ]; then
    echo "Error: Client '$CLIENT_ID' not found"
    exit 1
fi

# Find user
USER_ID=$(curl -sf "$KEYCLOAK_URL/admin/realms/$REALM/users?email=$USER_EMAIL&exact=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0].id')

if [ -z "$USER_ID" ] || [ "$USER_ID" = "null" ]; then
    echo "Error: User '$USER_EMAIL' not found"
    exit 1
fi

# Get all available client roles
AVAILABLE_ROLES=$(curl -sf "$KEYCLOAK_URL/admin/realms/$REALM/clients/$CLIENT_UUID/roles" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

# Build roles JSON array
ROLES_JSON="[]"
MISSING_ROLES=()

for role_name in "${ROLES_TO_ASSIGN[@]}"; do
    ROLE_DATA=$(echo "$AVAILABLE_ROLES" | jq -r ".[] | select(.name==\"$role_name\")")
    
    if [ -z "$ROLE_DATA" ]; then
        MISSING_ROLES+=("$role_name")
        continue
    fi
    
    ROLE_ID=$(echo "$ROLE_DATA" | jq -r '.id')
    ROLES_JSON=$(echo "$ROLES_JSON" | jq --arg id "$ROLE_ID" --arg name "$role_name" \
      '. += [{"id": $id, "name": $name}]')
done

# Check if any roles are missing
if [ ${#MISSING_ROLES[@]} -gt 0 ]; then
    echo "Error: Roles not found: ${MISSING_ROLES[*]}"
    echo "Run setup_keycloak_roles.sh to create roles first"
    exit 1
fi

# Check if there are valid roles to assign
if [ "$(echo "$ROLES_JSON" | jq 'length')" -eq 0 ]; then
    echo "Error: No valid roles to assign"
    exit 1
fi

# Assign roles
HTTP_CODE=$(curl -sf -w "%{http_code}" -o /dev/null -X POST \
  "$KEYCLOAK_URL/admin/realms/$REALM/users/$USER_ID/role-mappings/clients/$CLIENT_UUID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$ROLES_JSON")

if [ "$HTTP_CODE" = "204" ]; then
    echo "Success: Roles assigned to $USER_EMAIL"
    echo ""
    echo "Verify: $KEYCLOAK_URL/admin/master/console/#/$REALM/users/$USER_ID/role-mapping"
else
    echo "Error: Failed to assign roles (HTTP $HTTP_CODE)"
    exit 1
fi