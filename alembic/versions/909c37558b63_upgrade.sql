BEGIN;

CREATE SCHEMA "ApiKey";

CREATE TABLE IF NOT EXISTS "ApiKey"."ApiKeys" (
    id BIGSERIAL NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    hint VARCHAR(128) NOT NULL,
    hashed_key VARCHAR(128) NOT NULL,
    name VARCHAR(1024) NOT NULL,
    description VARCHAR(4096) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "ApiKeys_pkey" PRIMARY KEY (id)
);

CREATE UNIQUE INDEX "ApiKeys_hashed_key_idx" ON "ApiKey"."ApiKeys" (hashed_key);

CREATE TABLE IF NOT EXISTS "ApiKey"."Permissions" (
    id BIGSERIAL NOT NULL,
    name VARCHAR(1024) NOT NULL,
    description VARCHAR(4096) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "Permissions_pkey" PRIMARY KEY (id)
);

-- Seed common permissions for all services
INSERT INTO "ApiKey"."Permissions" (name, description) VALUES 
    ('aisearch', 'Access to AI-powered search service'),
    ('ocr', 'Access to OCR (Optical Character Recognition) service'),
    ('chat', 'Access to chat service'),
    ('ehr_summarize', 'Access to EHR summarization service'),
    ('rx_advisor', 'Access to prescription advisor service'),
    ('crawler', 'Access to web crawler service'),
    ('ehr', 'Access to Electronic Health Records service'),
    ('admin', 'Full administrative access to all resources');

CREATE UNIQUE INDEX "Permissions_name_idx" ON "ApiKey"."Permissions" (name);

CREATE TABLE IF NOT EXISTS "ApiKey"."ApiKeyPermissions" (
    apikey_id BIGINT NOT NULL,
    permission_id BIGINT NOT NULL,
    CONSTRAINT "ApiKeyPermissions_pkey" PRIMARY KEY (apikey_id, permission_id),
    CONSTRAINT "ApiKeyPermissions_apikey_id_fkey" FOREIGN KEY(apikey_id) REFERENCES "ApiKey"."ApiKeys" (id),
    CONSTRAINT "ApiKeyPermissions_permission_id_fkey" FOREIGN KEY(permission_id) REFERENCES "ApiKey"."Permissions" (id)
);

COMMIT;
