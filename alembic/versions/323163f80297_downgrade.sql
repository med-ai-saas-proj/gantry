BEGIN;

-- Running downgrade 323163f80297 -> a1b2c3d4e5f6

;;

DROP TRIGGER IF EXISTS trg_msg_seq ON "Conversation"."Messages";;

DROP FUNCTION IF EXISTS "Conversation".generate_msg_seq();;

ALTER TABLE "ApiKey"."ApiKeys" DROP CONSTRAINT "ApiKeys_project_id_fkey";

DROP INDEX "ApiKey"."ApiKeys_project_id_idx";

ALTER TABLE "ApiKey"."ApiKeys" DROP COLUMN project_id;

DROP INDEX "Conversation"."Messages_seq_id_idx";

DROP INDEX "Conversation"."Messages_conversation_id_idx";

DROP TABLE "Conversation"."Messages";

DROP INDEX "FileStorage"."Files_uuid_idx";

DROP INDEX "FileStorage"."Files_project_id_idx";

DROP TABLE "FileStorage"."Files";

DROP INDEX "Conversation"."Conversations_uuid_idx";

DROP INDEX "Conversation"."Conversations_project_id_idx";

DROP TABLE "Conversation"."Conversations";

DROP INDEX "Project"."Projects_uuid_idx";

DROP TABLE "Project"."Projects";

DROP SCHEMA IF EXISTS "Project" CASCADE;;

DROP SCHEMA IF EXISTS "Conversation" CASCADE;;

DROP SCHEMA IF EXISTS "FileStorage" CASCADE;;

UPDATE alembic_version SET version_num='a1b2c3d4e5f6' WHERE alembic_version.version_num = '323163f80297';

COMMIT;

