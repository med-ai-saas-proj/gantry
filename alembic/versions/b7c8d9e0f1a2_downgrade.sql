BEGIN;

ALTER TABLE "Organization"."Settings"
    ALTER COLUMN extra TYPE JSON
    USING extra::json;

ALTER TABLE "Organization"."Settings"
    ALTER COLUMN extra SET DEFAULT '{}';

DROP TABLE IF EXISTS "Project"."ProjectMembers";
DROP TABLE IF EXISTS "Project"."Projects";
DROP SCHEMA IF EXISTS "Project";

COMMIT;
