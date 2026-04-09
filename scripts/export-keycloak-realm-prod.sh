#! /usr/bin/env bash
docker run --rm                                     \
    --name keycloak_exporter                        \
    -v med-ai-saas_keycloak_data:/opt/keycloak/data \
    -v ./asset:/tmp/keycloak-export                 \
    quay.io/keycloak/keycloak:26.5.3                \
    export                     \
    --realm venera             \
    --dir /tmp/keycloak-export \
    --users realm_file
