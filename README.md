# Gantry

## Dev notes

### Pre-commit

- Pls install the pre commit hooks to ensure code quality
- To install run: `uv run pre-commit install`

### Formatting

- Run `./scripts/tidy.sh` to format and sort imports. THIS IS VERY IMPORTANT!!!

### How to quickly run the server (For development and testing) 

1. Check out [Getting API key](#getting-api-keys)
1. Copy [`example.gantry.toml`](./example.gantry.toml) to `gantry.toml` then find all the `#apikey` and put yours in.
1. Start DBs and other services: `docker compose -f compose.dev.yaml up`
1. Install dependency: `uv sync --dev --frozen`
1. Migrate DB: `uv run gantry server -f gantry.toml migrate`
1. Start server: `uv run gantry server -f gantry.toml`

**NOTES**:
- test username and password: `gantry-test-user` | `password` 

### Some useful scripts

- Generate `example.env` files for `.env` files: `scripts/gen-example-env.sh`
- Reset the database state: `scripts/reset-db.sh`. Remember to migrate and recreate the test account.

### Getting API keys

#### LLM

1. Go to <https://groq.com/> and get a free API key, this is `GROQ_API_KEY`

## Keycloak config

Gantry need 2 clients, 1 for the frontend (gantry front-end) and an service client for the backend (gantry-backend). You also need to config emails for sending invitation email. Here's the setup you need to go through.

1. Create clients:
  1. Go to `Clients > Create client` and uses the following config: 
    - Client id: `gantry-frontend`
    - PKCE: S256
    - Client authentication: off
    - Authentication flow: Standard flow
    - Put your frontend's URLs in Access Settings
  1. Create another client with the following config:
    - Client id: `gantry-backend`
    - Client authentication: On
    - Authentication flow: Service account roles
  1. After creating the `gantry-backend` client to the following:
    1. Go to `credentials tab` and copy the client secret
    1. Go to `Service account roles > service-account-gantry-backend > Role mapping`
    1. Assign the following client roles:
      - manage-users
      - view-users
      - view-clients
      - manage-realm
1. Enable Organization feature: Go to `realm settings > general` and enable organization
1. Put user's organization and permission in JWT:
  1. Go to `realm settings > user profile` to create 2 attributes
    1. org_permissions:
      - name: org_permissions
      - multivalued: Yes
      - Who can edit?: Admin
      - Who can view?: Admin
    1. project_permissions
      - name: project_permissions
      - multivalued: Yes
      - Who can edit?: Admin
      - Who can view?: Admin
  1. Go to `Client scopes`
  1. Click on organization
  1. Change type to `Default`
  1. Go to `Mappers` tab and change the following settings:
    - Claim JSON type: JSON
    - Add organization attributes: On
    - Add organization id: On
