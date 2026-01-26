#!/bin/bash
# Create RBAC roles for Keycloak client

set -e

# Configuration
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-dev}"
CLIENT_ID="${CLIENT_ID:-med-ai-saas-app}"
ADMIN_USERNAME="${KEYCLOAK_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"

echo "Creating roles for client: $CLIENT_ID"

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

# Define roles
declare -A ROLES=(
    ["super_admin"]="Full access to all resources"
    ["org.admin"]="Organization administrator"
    ["org.member"]="Organization member"
    ["org.viewer"]="Organization viewer"
    ["member.admin"]="Full member management"
    ["member.add"]="Add members"
    ["member.edit"]="Edit members"
    ["member.delete"]="Delete members"
    ["member.view"]="View members"
    ["permission.admin"]="Full permission management"
    ["permission.create"]="Create permissions"
    ["permission.edit"]="Edit permissions"
    ["permission.delete"]="Delete permissions"
    ["permission.view"]="View permissions"
    ["apikey.admin"]="Full API key management"
    ["apikey.create"]="Create API keys"
    ["apikey.edit"]="Edit API keys"
    ["apikey.delete"]="Delete API keys"
    ["apikey.view"]="View API keys"
    ["user.admin"]="Full user management"
    ["user.create"]="Create users"
    ["user.edit"]="Edit users"
    ["user.delete"]="Delete users"
    ["user.view"]="View users"
    ["audit.view"]="View audit logs"
    ["audit.export"]="Export audit logs"
    ["settings.admin"]="Full settings access"
    ["settings.edit"]="Edit settings"
    ["settings.view"]="View settings"
)

CREATED=0
SKIPPED=0

for role_name in "${!ROLES[@]}"; do
    description="${ROLES[$role_name]}"
    
    # Check if role exists
    HTTP_CODE=$(curl -sf -w "%{http_code}" -o /dev/null \
      "$KEYCLOAK_URL/admin/realms/$REALM/clients/$CLIENT_UUID/roles/$role_name" \
      -H "Authorization: Bearer $ADMIN_TOKEN" 2>/dev/null || echo "404")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "  Skip: $role_name (exists)"
        ((SKIPPED++))
    else
        # Create role
        HTTP_CODE=$(curl -sf -w "%{http_code}" -o /dev/null -X POST \
          "$KEYCLOAK_URL/admin/realms/$REALM/clients/$CLIENT_UUID/roles" \
          -H "Authorization: Bearer $ADMIN_TOKEN" \
          -H "Content-Type: application/json" \
          -d "{\"name\":\"$role_name\",\"description\":\"$description\"}")
        
        if [ "$HTTP_CODE" = "201" ]; then
            echo "  Created: $role_name"
            ((CREATED++))
        else
            echo "  Failed: $role_name (HTTP $HTTP_CODE)"
        fi
    fi
done

echo ""
echo "Summary: Created $CREATED | Skipped $SKIPPED | Total ${#ROLES[@]}"