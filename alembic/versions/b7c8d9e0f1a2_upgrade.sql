BEGIN;

CREATE SCHEMA IF NOT EXISTS "Project";

CREATE TABLE IF NOT EXISTS "Project"."Projects" (
    id BIGSERIAL NOT NULL,
    uuid UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(1024),
    organization_id VARCHAR(128) NOT NULL,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "Projects_pkey" PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS "Projects_uuid_idx" ON "Project"."Projects" (uuid);
CREATE INDEX IF NOT EXISTS "Projects_organization_id_idx" ON "Project"."Projects" (organization_id);

CREATE TABLE IF NOT EXISTS "Project"."ProjectMembers" (
    project_id BIGINT NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    joined_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "ProjectMembers_pkey" PRIMARY KEY (project_id, user_id),
    CONSTRAINT "ProjectMembers_project_id_fkey"
        FOREIGN KEY (project_id) REFERENCES "Project"."Projects" (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "ProjectMembers_user_id_idx" ON "Project"."ProjectMembers" (user_id);

ALTER TABLE "Organization"."Settings"
    ALTER COLUMN extra TYPE JSONB
    USING extra::jsonb;

ALTER TABLE "Organization"."Settings"
    ALTER COLUMN extra SET DEFAULT '{}'::jsonb;

COMMIT;
