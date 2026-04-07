BEGIN;

-- Running upgrade a1b2c3d4e5f6 -> 323163f80297

;;

CREATE SCHEMA IF NOT EXISTS "Project";

CREATE SCHEMA IF NOT EXISTS "Conversation";

CREATE SCHEMA IF NOT EXISTS "FileStorage";

CREATE TABLE "Project"."Projects" (
    id BIGSERIAL NOT NULL,
    uuid UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(1024),
    organization_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "Projects_pkey" PRIMARY KEY (id)
);

CREATE UNIQUE INDEX "Projects_uuid_idx" ON "Project"."Projects" (uuid);

CREATE TABLE "Conversation"."Conversations" (
    id BIGSERIAL NOT NULL,
    uuid UUID NOT NULL,
    project_id BIGINT NOT NULL,
    extra_metadata JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "Conversations_pkey" PRIMARY KEY (id),
    CONSTRAINT "Conversations_project_id_fkey" FOREIGN KEY(project_id) REFERENCES "Project"."Projects" (id) ON DELETE CASCADE
);

CREATE INDEX "Conversations_project_id_idx" ON "Conversation"."Conversations" (project_id);

CREATE UNIQUE INDEX "Conversations_uuid_idx" ON "Conversation"."Conversations" (uuid);

CREATE TYPE "FileStorage".filestatus AS ENUM ('UPLOADING', 'AVAILABLE', 'DELETED');

CREATE TABLE "FileStorage"."Files" (
    id BIGSERIAL NOT NULL,
    uuid UUID NOT NULL,
    original_filename VARCHAR(256) NOT NULL,
    filepath VARCHAR(512) NOT NULL,
    project_id BIGINT NOT NULL,
    mime_type VARCHAR(64) NOT NULL,
    size_in_bytes INTEGER NOT NULL,
    status "FileStorage".filestatus NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    extra_metadata JSONB,
    CONSTRAINT "Files_pkey" PRIMARY KEY (id),
    CONSTRAINT "Files_project_id_fkey" FOREIGN KEY(project_id) REFERENCES "Project"."Projects" (id) ON DELETE CASCADE
);

CREATE INDEX "Files_project_id_idx" ON "FileStorage"."Files" (project_id);

CREATE UNIQUE INDEX "Files_uuid_idx" ON "FileStorage"."Files" (uuid);

CREATE TABLE "Conversation"."Messages" (
    id BIGSERIAL NOT NULL,
    uuid UUID NOT NULL,
    conversation_id BIGINT NOT NULL,
    seq_id BIGINT NOT NULL,
    kind VARCHAR(32),
    parts JSONB NOT NULL,
    model_name VARCHAR(32),
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    run_id VARCHAR(128),
    CONSTRAINT "Messages_pkey" PRIMARY KEY (id),
    CONSTRAINT "Messages_conversation_id_fkey" FOREIGN KEY(conversation_id) REFERENCES "Conversation"."Conversations" (id) ON DELETE CASCADE
);

CREATE INDEX "Messages_conversation_id_idx" ON "Conversation"."Messages" (conversation_id);

CREATE INDEX "Messages_seq_id_idx" ON "Conversation"."Messages" (seq_id);

CREATE INDEX "Messages_uuid_idx" ON "Conversation"."Messages" (uuid);

ALTER TABLE "ApiKey"."ApiKeys" ADD COLUMN project_id BIGINT NOT NULL;

CREATE INDEX "ApiKeys_project_id_idx" ON "ApiKey"."ApiKeys" (project_id);

ALTER TABLE "ApiKey"."ApiKeys" ADD CONSTRAINT "ApiKeys_project_id_fkey" FOREIGN KEY(project_id) REFERENCES "Project"."Projects" (id);

-- CREATE OR REPLACE FUNCTION "Conversation".generate_msg_seq()
--     RETURNS TRIGGER AS $$
--         BEGIN
--             SELECT COALESCE(MAX(seq_id), 0) + 1
--             INTO NEW.seq_id
--             FROM "Conversation"."Messages"
--             WHERE conversation_id = NEW.conversation_id;
--             RETURN NEW;
--         END;
--     $$ LANGUAGE plpgsql;;

-- CREATE TRIGGER trg_msg_seq
-- BEFORE INSERT ON "Conversation"."Messages"
-- FOR EACH ROW EXECUTE FUNCTION "Conversation".generate_msg_seq();;

-- UPDATE alembic_version SET version_num='323163f80297' WHERE alembic_version.version_num = 'a1b2c3d4e5f6';

COMMIT;
