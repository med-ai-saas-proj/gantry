#!/bin/bash
# Get authentication token from Keycloak using password grant

set -e

# Configuration
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-dev}"
CLIENT_ID="${CLIENT_ID:-med-ai-saas-app}"
USERNAME="${1:-${KEYCLOAK_USERNAME}}"
PASSWORD="${2:-${KEYCLOAK_PASSWORD}}"

if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
    cat << EOF
Usage: $0 <username> <password>

Or set environment variables:
  export KEYCLOAK_USERNAME='user@example.com'
  export KEYCLOAK_PASSWORD='password'

Current config:
  URL: $KEYCLOAK_URL
  Realm: $REALM
  Client: $CLIENT_ID
EOF
    exit 1
fi

# Request token
TOKEN_URL="$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token"

RESPONSE=$(curl -sf -X POST "$TOKEN_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=$CLIENT_ID" \
  -d "username=$USERNAME" \
  -d "password=$PASSWORD" \
  -d "grant_type=password" 2>&1) || {
    
    # Handle common errors
    if echo "$RESPONSE" | grep -q "Connection refused"; then
        echo "Error: Cannot connect to $KEYCLOAK_URL"
        echo "Ensure Keycloak is running"
        exit 1
    fi
    
    echo "Error: Authentication failed"
    echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
    
    if echo "$RESPONSE" | grep -q "unauthorized_client"; then
        cat << EOF

Fix: Enable 'Direct Access Grants' in Keycloak
  1. Go to: $KEYCLOAK_URL/admin
  2. Navigate: $REALM → Clients → $CLIENT_ID → Settings
  3. Enable: Direct access grants
  4. Save
EOF
    fi
    exit 1
}

# Extract tokens
ACCESS_TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')
REFRESH_TOKEN=$(echo "$RESPONSE" | jq -r '.refresh_token')
EXPIRES_IN=$(echo "$RESPONSE" | jq -r '.expires_in')

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" = "null" ]; then
    echo "Error: Failed to get access token"
    echo "$RESPONSE" | jq '.'
    exit 1
fi

# Save token
echo "$ACCESS_TOKEN" > /tmp/keycloak_token.txt

# Output
echo "Access Token:"
echo "$ACCESS_TOKEN"
echo ""
echo "Expires in: $EXPIRES_IN seconds ($((EXPIRES_IN / 60)) minutes)"
echo "Saved to: /tmp/keycloak_token.txt"
echo ""
echo "Usage:"
echo "  export AUTH_TOKEN=\"$ACCESS_TOKEN\""
echo "  # or"
echo "  export AUTH_TOKEN=\$(cat /tmp/keycloak_token.txt)"
echo ""
echo "Test:"
echo "  curl -H \"Authorization: Bearer \$AUTH_TOKEN\" http://localhost:8000/api/endpoint"