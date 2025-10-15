BEGIN;

DROP INDEX IF EXISTS idx_message_citations_messages_pk;
DROP TABLE IF EXISTS message_citations;

DROP TABLE IF EXISTS message_citation_types;

DROP INDEX IF EXISTS idx_message_parts_messages_pk;
ALTER TABLE message_parts DROP CONSTRAINT IF EXISTS constraint_uq_message_parts_message_pk_file_name;
DROP TABLE IF EXISTS message_parts;

DROP INDEX IF EXISTS idx_messages_created_at;
DROP INDEX IF EXISTS idx_messages_conversation_pk;
DROP TABLE IF EXISTS messages;

DROP TABLE IF EXISTS message_roles;

DROP INDEX IF EXISTS idx_ai_models_name;
DROP TABLE IF EXISTS ai_models;

DROP INDEX IF EXISTS idx_base_ai_models_name;
DROP TABLE IF EXISTS base_ai_models;

DROP TABLE IF EXISTS ai_providers;

DROP INDEX IF EXISTS idx_conversations_updated_at;
DROP INDEX IF EXISTS idx_conversations_user_id;
DROP INDEX IF EXISTS idx_conversations_conversation_id;
DROP TABLE IF EXISTS conversations;

END;