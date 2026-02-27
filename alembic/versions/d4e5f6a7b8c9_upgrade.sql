BEGIN;

CREATE TABLE IF NOT EXISTS "Organization"."Metadata" (
    org_id VARCHAR(128) NOT NULL,
    name VARCHAR(256) NOT NULL,
    owner_id VARCHAR(128) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "Metadata_pkey" PRIMARY KEY (org_id)
);

CREATE INDEX IF NOT EXISTS "Metadata_owner_id_idx"
    ON "Organization"."Metadata" (owner_id);

COMMIT;
