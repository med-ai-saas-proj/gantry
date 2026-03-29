BEGIN;

CREATE SCHEMA "ApiKey";

CREATE TABLE IF NOT EXISTS "ApiKey"."ApiKeys" (
    id BIGSERIAL NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    hint VARCHAR(128) NOT NULL,
    hashed_key VARCHAR(128) NOT NULL,
    name VARCHAR(1024) NOT NULL,
    description VARCHAR(4096) NOT NULL,
    permissions TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "ApiKeys_pkey" PRIMARY KEY (id)
);

CREATE UNIQUE INDEX "ApiKeys_hashed_key_idx" ON "ApiKey"."ApiKeys" (hashed_key);

COMMIT;
