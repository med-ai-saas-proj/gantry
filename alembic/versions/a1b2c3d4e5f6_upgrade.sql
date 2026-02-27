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
    requested_by VARCHAR(128) NOT NULL,
    requested_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    cancel_before TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    cancelled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "DeletionRequests_pkey" PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS "DeletionRequests_org_id_idx" ON "Organization"."DeletionRequests" (org_id);

CREATE TABLE IF NOT EXISTS "Organization"."Invitations" (
    id BIGSERIAL NOT NULL,
    org_id VARCHAR(128) NOT NULL,
    email VARCHAR(320) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    invited_by VARCHAR(128),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "Invitations_pkey" PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS "Invitations_org_id_idx" ON "Organization"."Invitations" (org_id);

COMMIT;
