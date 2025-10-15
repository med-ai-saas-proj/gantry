BEGIN;

CREATE TABLE conversations (
    pk BIGSERIAL PRIMARY KEY,
    id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

COMMENT ON COLUMN conversations.metadata IS 'Key-value string pairs. Application-level limits: 16 pairs, max key length 64, max value length 512.';

CREATE INDEX idx_conversations_conversation_id ON conversations (id);
CREATE INDEX idx_conversations_user_id ON conversations (user_id);
CREATE INDEX idx_conversations_updated_at ON conversations (updated_at DESC);

CREATE VIEW conversations_not_deleted AS
SELECT pk, id, user_id, created_at, updated_at, metadata
FROM conversations
WHERE conversations.deleted_at IS NULL;

CREATE TABLE ai_providers (
    pk SMALLSERIAL PRIMARY KEY,
    name VARCHAR(64)
);

INSERT INTO ai_providers (name) VALUES
('anthropic'),
('openai'),
('google'),
('self_host');

CREATE TABLE base_ai_models (
    pk SMALLSERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    provider_pk SMALLINT NOT NULL REFERENCES ai_providers(pk),
    model_id VARCHAR(255) NOT NULL,
    rate_per_sec SMALLINT NOT NULL
);
CREATE INDEX idx_base_ai_models_name ON base_ai_models(name);

CREATE TABLE ai_models (
    pk SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) UNIQUE NOT NULL,
    base_ai_model_pk SMALLINT NOT NULL REFERENCES base_ai_models(pk),
    instruction TEXT NOT NULL
);
CREATE INDEX idx_ai_models_user_id_name ON ai_models(user_id, name);
ALTER TABLE ai_models ADD CONSTRAINT constraint_ai_models_user_id_name_unique UNIQUE (user_id, name)

CREATE TABLE message_roles (
    pk SMALLSERIAL PRIMARY KEY,
    role VARCHAR(16) UNIQUE NOT NULL
);

INSERT INTO message_roles (role) VALUES
('user'),
('assistant'),
('tool');
-- ('system'),
-- ('developer');

CREATE TABLE messages (
    pk BIGSERIAL PRIMARY KEY,
    id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    conversation_pk BIGINT NOT NULL REFERENCES conversations(pk),
    ai_model_pk BIGINT NOT NULL REFERENCES ai_models(pk),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    role_pk SMALLINT NOT NULL REFERENCES message_roles(pk),
    content_text TEXT,
    tool_call JSONB
);

CREATE INDEX idx_messages_conversation_pk ON messages(conversation_pk);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);

CREATE TABLE message_parts (
    pk BIGSERIAL PRIMARY KEY,
    message_pk BIGINT NOT NULL REFERENCES messages(pk) ON UPDATE CASCADE,
    index SMALLINT NOT NULL,
    mime_type VARCHAR(255) NOT NULL,
    file_name VARCHAR(255) NOT NULL
);

CREATE INDEX idx_message_parts_messages_pk ON message_parts(message_pk);
ALTER TABLE message_parts ADD CONSTRAINT constraint_uq_message_parts_message_pk_file_name
UNIQUE (message_pk, file_name);


CREATE TABLE message_citation_types (
    pk SMALLSERIAL PRIMARY KEY,
    reference_type VARCHAR(16) NOT NULL UNIQUE
);
INSERT INTO message_citation_types (reference_type) VALUES
('document'),
('webpage'),
('inline_text');

CREATE TABLE message_citations (
    pk BIGSERIAL PRIMARY KEY,
    message_pk BIGINT NOT NULL REFERENCES messages(pk),
    start_index INTEGER NOT NULL,
    end_index INTEGER NOT NULL,
    reference_type_pk SMALLSERIAL NOT NULL REFERENCES message_citation_types ON UPDATE CASCADE,
    title VARCHAR(512) NOT NULL,
    src VARCHAR(2048) NOT NULL,
    content TEXT NOT NULL
);
CREATE INDEX idx_message_citations_messages_pk ON message_citations(message_pk);

END;