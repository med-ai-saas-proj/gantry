BEGIN;

DROP INDEX "ApiKey"."ApiKeys_hashed_key_idx";
DROP TABLE "ApiKey"."ApiKeys";
DROP SCHEMA "ApiKey";

COMMIT;
