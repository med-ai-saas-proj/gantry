BEGIN;

ALTER TABLE "Organization"."Invitations"
    DROP COLUMN IF EXISTS permissions;

DROP TABLE IF EXISTS "Organization"."Projects";

COMMIT;
