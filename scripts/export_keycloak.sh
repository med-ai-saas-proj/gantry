#!/bin/bash
# Complete Keycloak realm export including users and credentials

set -e

# Configuration
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-dev}"
ADMIN_USERNAME="${KEYCLOAK_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
OUTPUT_DIR="${OUTPUT_DIR:-./asset}"
OUTPUT_FILE="${OUTPUT_FILE:-${REALM}-realm.json}"

echo "Exporting realm: $REALM"
mkdir -p "$OUTPUT_DIR"

# Get admin token
echo "Authenticating..."
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

# Export realm with users
echo "Exporting realm configuration and users..."
curl -sf -X POST "$KEYCLOAK_URL/admin/realms/$REALM/partial-export?exportGroupsAndRoles=true&exportClients=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -o "$OUTPUT_DIR/realm-base.json"

# Get users with full details
echo "Fetching users..."
curl -sf -X GET "$KEYCLOAK_URL/admin/realms/$REALM/users?briefRepresentation=false" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o "$OUTPUT_DIR/users.json"

USER_COUNT=$(jq 'length' "$OUTPUT_DIR/users.json")
echo "Found $USER_COUNT users"

# Get credentials for each user
if [ "$USER_COUNT" -gt 0 ]; then
    echo "Fetching user credentials..."
    jq -c '.[]' "$OUTPUT_DIR/users.json" | while IFS= read -r user; do
        USER_ID=$(echo "$user" | jq -r '.id')
        CREDS=$(curl -sf -X GET "$KEYCLOAK_URL/admin/realms/$REALM/users/$USER_ID/credentials" \
          -H "Authorization: Bearer $ADMIN_TOKEN")
        echo "$user" | jq --argjson c "$CREDS" '. + {credentials: $c}'
    done | jq -s '.' > "$OUTPUT_DIR/users-final.json"
else
    echo "[]" > "$OUTPUT_DIR/users-final.json"
fi

# Get client secrets for confidential clients
echo "Fetching client secrets..."
jq -c '.clients[] | select(.publicClient == false)' "$OUTPUT_DIR/realm-base.json" | while IFS= read -r client; do
    CLIENT_ID=$(echo "$client" | jq -r '.id')
    SECRET=$(curl -sf -X GET "$KEYCLOAK_URL/admin/realms/$REALM/clients/$CLIENT_ID/client-secret" \
      -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.value')
    echo "$CLIENT_ID:$SECRET"
done > "$OUTPUT_DIR/secrets.txt"

# Merge realm, users, and client secrets
echo "Creating final export..."
jq --argfile users "$OUTPUT_DIR/users-final.json" '. + {users: $users}' \
  "$OUTPUT_DIR/realm-base.json" > "$OUTPUT_DIR/temp.json"

# Add client secrets back
while IFS=: read -r CLIENT_ID SECRET; do
    jq --arg id "$CLIENT_ID" --arg secret "$SECRET" \
      '(.clients[] | select(.id == $id)) += {secret: $secret}' \
      "$OUTPUT_DIR/temp.json" > "$OUTPUT_DIR/temp2.json"
    mv "$OUTPUT_DIR/temp2.json" "$OUTPUT_DIR/temp.json"
done < "$OUTPUT_DIR/secrets.txt"

mv "$OUTPUT_DIR/temp.json" "$OUTPUT_DIR/$OUTPUT_FILE"

# Cleanup temp files
rm -f "$OUTPUT_DIR/realm-base.json" "$OUTPUT_DIR/users.json" "$OUTPUT_DIR/users-final.json" "$OUTPUT_DIR/secrets.txt"

# Summary
SIZE=$(du -h "$OUTPUT_DIR/$OUTPUT_FILE" | cut -f1)
FINAL_COUNT=$(jq '.users | length' "$OUTPUT_DIR/$OUTPUT_FILE")
echo ""
echo "Export complete: $OUTPUT_DIR/$OUTPUT_FILE ($SIZE)"
echo "Users: $FINAL_COUNT | Clients: $(jq '.clients | length' "$OUTPUT_DIR/$OUTPUT_FILE")"
echo ""
echo "WARNING: Contains hashed passwords and secrets - keep secure!"