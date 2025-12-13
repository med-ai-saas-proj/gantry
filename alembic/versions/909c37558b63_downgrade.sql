BEGIN;

DROP TABLE "ApiKey"."ApiKeyPermissions";
DROP INDEX "ApiKey"."Permissions_name_idx";
DROP TABLE "ApiKey"."Permissions";
DROP INDEX "ApiKey"."ApiKeys_hashed_key_idx";
DROP TABLE "ApiKey"."ApiKeys";
DROP SCHEMA "ApiKey"

COMMIT;
