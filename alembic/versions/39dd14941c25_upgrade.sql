BEGIN;

CREATE SCHEMA "ApiKey";

CREATE TABLE IF NOT EXISTS "ApiKey"."ApiKeys" (
    id BIGSERIAL NOT NULL,
    owner_id TEXT NOT NULL,
    hashed_key TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "ApiKeys_pkey" PRIMARY KEY (id)
);

CREATE UNIQUE INDEX "ApiKeys_hashed_key_idx" ON "ApiKey"."ApiKeys" (hashed_key);

CREATE TABLE IF NOT EXISTS "ApiKey"."Permissions" (
    id BIGSERIAL NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "Permissions_pkey" PRIMARY KEY (id)
);

CREATE UNIQUE INDEX "Permissions_name_idx" ON "ApiKey"."Permissions" (name);

CREATE TABLE IF NOT EXISTS "ApiKey"."ApiKeyPermissions" (
    apikey_id BIGINT NOT NULL,
    permission_id BIGINT NOT NULL,
    CONSTRAINT "ApiKeyPermissions_pkey" PRIMARY KEY (apikey_id, permission_id),
    CONSTRAINT "ApiKeyPermissions_apikey_id_fkey" FOREIGN KEY(apikey_id) REFERENCES "ApiKey"."ApiKeys" (id),
    CONSTRAINT "ApiKeyPermissions_permission_id_fkey" FOREIGN KEY(permission_id) REFERENCES "ApiKey"."Permissions" (id)
);

COMMIT;
