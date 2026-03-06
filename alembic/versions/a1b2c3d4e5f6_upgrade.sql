BEGIN;

CREATE SCHEMA IF NOT EXISTS "Organization";

CREATE TABLE IF NOT EXISTS "Organization"."Settings" (
    org_id VARCHAR(128) NOT NULL,
    rate_limit INTEGER,
    extra JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "Settings_pkey" PRIMARY KEY (org_id)
);

CREATE TABLE IF NOT EXISTS "Organization"."DeletionRequests" (
    id BIGSERIAL NOT NULL,
    org_id VARCHAR(128) NOT NULL,
    requested_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "DeletionRequests_pkey" PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS "DeletionRequests_org_id_idx" ON "Organization"."DeletionRequests" (org_id);

COMMIT;
