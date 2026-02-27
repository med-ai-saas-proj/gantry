BEGIN;

CREATE TABLE IF NOT EXISTS "Organization"."Projects" (
    id BIGSERIAL NOT NULL,
    org_id VARCHAR(128) NOT NULL,
    name VARCHAR(256) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "Projects_pkey" PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS "Projects_org_id_idx"
    ON "Organization"."Projects" (org_id);

ALTER TABLE "Organization"."Invitations"
    ADD COLUMN IF NOT EXISTS permissions JSON NOT NULL DEFAULT '[]';

COMMIT;
