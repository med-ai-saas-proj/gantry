BEGIN;
CREATE SCHEMA IF NOT EXISTS "Billing";
CREATE TABLE "Billing"."BillingInvoices" (
    id BIGSERIAL NOT NULL,
    uuid UUID NOT NULL,
    organization_id VARCHAR(128) NOT NULL,
    billing_period DATE NOT NULL,
    total_amount NUMERIC(18, 8) NOT NULL,
    provider_invoice_id VARCHAR(128) NOT NULL,
    paid_at TIMESTAMP WITHOUT TIME ZONE,
    details JSONB NOT NULL,
    used_credits NUMERIC(18, 8) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "BillingInvoices_pkey" PRIMARY KEY (id),
    CONSTRAINT "BillingInvoices_billing_period_uq" UNIQUE (billing_period)
);
CREATE INDEX "BillingInvoices_organization_id_idx" ON "Billing"."BillingInvoices" (organization_id);
CREATE UNIQUE INDEX "BillingInvoices_uuid_idx" ON "Billing"."BillingInvoices" (uuid);
CREATE TYPE billingsourceprovider AS ENUM ('STRIPE', 'PAYPAL');
CREATE TYPE billingsourcestate AS ENUM ('PENDING', 'ACTIVE', 'DELETED');
CREATE TABLE "Billing"."BillingSources" (
    id BIGSERIAL NOT NULL,
    uuid UUID NOT NULL,
    organization_id VARCHAR(128) NOT NULL,
    source_type billingsourceprovider NOT NULL,
    provider_id VARCHAR(128) NOT NULL,
    status billingsourcestate DEFAULT 'PENDING' NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "BillingSources_pkey" PRIMARY KEY (id)
);
CREATE INDEX "BillingSources_organization_id_idx" ON "Billing"."BillingSources" (organization_id);
CREATE UNIQUE INDEX "BillingSources_uuid_idx" ON "Billing"."BillingSources" (uuid);
CREATE TABLE "Billing"."BillingTransactions" (
    id BIGSERIAL NOT NULL,
    uuid UUID NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    apikey_id BIGINT NOT NULL,
    project_id BIGINT,
    organization_id VARCHAR(128) NOT NULL,
    amount NUMERIC(18, 8) NOT NULL,
    captured_at TIMESTAMP WITHOUT TIME ZONE,
    details JSONB NOT NULL,
    CONSTRAINT "BillingTransactions_pkey" PRIMARY KEY (id, created_at)
);
CREATE INDEX "BillingTransactions_apikey_id_idx" ON "Billing"."BillingTransactions" (apikey_id);
CREATE INDEX "BillingTransactions_organization_id_idx" ON "Billing"."BillingTransactions" (organization_id);
CREATE INDEX "BillingTransactions_project_id_idx" ON "Billing"."BillingTransactions" (project_id);
CREATE INDEX "BillingTransactions_uuid_idx" ON "Billing"."BillingTransactions" (uuid);
CREATE TABLE "Billing"."Credits" (
    id BIGSERIAL NOT NULL,
    uuid UUID NOT NULL,
    organization_id VARCHAR(128) NOT NULL,
    name VARCHAR(128) NOT NULL,
    note VARCHAR(512),
    start_date DATE NOT NULL,
    expired_date DATE NOT NULL,
    amount NUMERIC(18, 8) NOT NULL,
    current_spent NUMERIC(18, 8) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "Credits_pkey" PRIMARY KEY (id)
);
CREATE INDEX "Credits_organization_id_idx" ON "Billing"."Credits" (organization_id);
CREATE UNIQUE INDEX "Credits_uuid_idx" ON "Billing"."Credits" (uuid);
CREATE TYPE "Billing".spendinglimittype AS ENUM ('MONTHLY');
CREATE TABLE "Billing"."SpendingLimits" (
    id BIGSERIAL NOT NULL,
    uuid UUID NOT NULL,
    organization_id VARCHAR(128) NOT NULL,
    project_id BIGINT,
    limit_type "Billing".spendinglimittype NOT NULL,
    "limit" NUMERIC(18, 8),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "SpendingLimits_pkey" PRIMARY KEY (id),
    CONSTRAINT uq_spending_limit UNIQUE (organization_id, project_id)
);
CREATE INDEX "SpendingLimits_organization_id_idx" ON "Billing"."SpendingLimits" (organization_id);
CREATE UNIQUE INDEX "SpendingLimits_project_id_idx" ON "Billing"."SpendingLimits" (project_id);
CREATE UNIQUE INDEX "SpendingLimits_uuid_idx" ON "Billing"."SpendingLimits" (uuid);
CREATE UNIQUE INDEX ix_spending_limits_org ON "Billing"."SpendingLimits" (organization_id)
WHERE project_id IS NULL;
CREATE TABLE "Billing"."BillingInvoiceLineItems" (
    id BIGSERIAL NOT NULL,
    uuid UUID NOT NULL,
    invoice_id BIGINT NOT NULL,
    description VARCHAR(256) NOT NULL,
    amount NUMERIC(18, 8) NOT NULL,
    project_id BIGINT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT "BillingInvoiceLineItems_pkey" PRIMARY KEY (id),
    CONSTRAINT "BillingInvoiceLineItems_invoice_id_fkey" FOREIGN KEY (invoice_id) REFERENCES "Billing"."BillingInvoices" (id) ON DELETE CASCADE
);
CREATE INDEX "BillingInvoiceLineItems_invoice_id_idx" ON "Billing"."BillingInvoiceLineItems" (invoice_id);
CREATE INDEX "BillingInvoiceLineItems_project_id_idx" ON "Billing"."BillingInvoiceLineItems" (project_id);
CREATE UNIQUE INDEX "BillingInvoiceLineItems_uuid_idx" ON "Billing"."BillingInvoiceLineItems" (uuid);
SELECT create_hypertable (
        '"Billing"."BillingTransactions"',
        'created_at',
        chunk_time_interval => INTERVAL '7 days'
    );
;
ALTER TABLE "Billing"."BillingTransactions"
SET (
        timescaledb.compress,
        timescaledb.compress_segmentby = 'apikey_id, project_id, organization_id',
        timescaledb.compress_orderby = 'created_at DESC'
    );
;
SELECT add_compression_policy (
        '"Billing"."BillingTransactions"',
        INTERVAL '14 days'
    );
;
CREATE MATERIALIZED VIEW "Billing".daily_billing_summary WITH (timescaledb.continuous) AS
SELECT time_bucket ('1 day', created_at) AS bucket,
    apikey_id,
    project_id,
    organization_id,
    SUM(amount) AS total_amount,
    COUNT(*) AS transaction_count
FROM "Billing"."BillingTransactions"
GROUP BY bucket,
    apikey_id,
    project_id,
    organization_id with no data;
;
ALTER MATERIALIZED VIEW "Billing".daily_billing_summary
SET (
        timescaledb.materialized_only = false
    );
;
SELECT add_continuous_aggregate_policy (
        '"Billing".daily_billing_summary',
        start_offset => INTERVAL '3 days',
        end_offset => INTERVAL '0 seconds',
        schedule_interval => INTERVAL '1 hour'
    );
COMMIT;