#! /bin/bash
docker compose -f compose.dev.yaml down --volumes
docker compose -f compose.dev.yaml up -d
/bin/bash setup-test-account.sh