#! /usr/bin/env bash
docker run -p 8080:8080 -v med-ai-saas_keycloak_data:/opt/keycloak/data -v ./contributing-docs:/tmp/keycloak-export   -e KEYCLOAK_ADMIN=admin   -e KEYCLOAK_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:26.5.3 export --realm gantry --dir /tmp/keycloak-export --users realm_file
