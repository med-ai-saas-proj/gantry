from __future__ import annotations

from datetime import timedelta

import asyncpg
import pytest
import sqlalchemy as sa
from pyrusult import ResultStatus
from sqlalchemy.ext.asyncio import create_async_engine

from gantry.db.factories import getRedis, getRedisBinary, getRedisConnectionPool
from gantry.db.repositories import RedisCacheRepository
from gantry.db.settings import getDBSettings

pytestmark = pytest.mark.integration


def _engine():
    return create_async_engine(
        getDBSettings().timescale_connection_uri.encoded_string()
    )


def _decode(value):
    return value.decode() if isinstance(value, bytes) else value


@pytest.mark.asyncio
async def test_management_storage_accepts_queries_after_migration(migrated_management_storage) -> None:
    engine = _engine()
    async with engine.connect() as connection:
        result = await connection.execute(sa.text("SELECT 1"))
    await engine.dispose()

    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_management_migration_version_is_recorded(migrated_management_storage) -> None:
    engine = _engine()
    async with engine.connect() as connection:
        result = await connection.execute(
            sa.text("SELECT version_num FROM alembic_version")
        )
    await engine.dispose()

    assert result.scalar_one()


@pytest.mark.asyncio
async def test_management_migration_is_idempotent(
    migrated_management_storage_twice,
) -> None:
    engine = _engine()
    async with engine.connect() as connection:
        result = await connection.execute(
            sa.text("SELECT COUNT(*) FROM alembic_version")
        )
    await engine.dispose()

    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_management_schemas_and_api_key_uuid_contract_exist(migrated_management_storage) -> None:
    engine = _engine()
    async with engine.connect() as connection:
        schemas = {
            row[0]
            for row in (
                await connection.execute(
                    sa.text(
                        "SELECT schema_name FROM information_schema.schemata "
                        "WHERE schema_name IN ("
                        "'ApiKey', 'Project', 'Organization', 'Billing', "
                        "'Conversation', 'FileStorage', 'Rag'"
                        ")"
                    )
                )
            ).fetchall()
        }
        columns = {
            (row.table_schema, row.table_name, row.column_name)
            for row in (
                await connection.execute(
                    sa.text(
                        "SELECT table_schema, table_name, column_name "
                        "FROM information_schema.columns "
                        "WHERE (table_schema, table_name, column_name) IN ("
                        "('ApiKey', 'ApiKeys', 'uuid'),"
                        "('ApiKey', 'ApiKeys', 'hashed_key'),"
                        "('Project', 'Projects', 'uuid'),"
                        "('Billing', 'BillingTransactions', 'uuid'),"
                        "('Rag', 'Metadata', 'model_name')"
                        ")"
                    )
                )
            ).fetchall()
        }
        api_key_uuid = (
            await connection.execute(
                sa.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'ApiKey' "
                    "AND table_name = 'ApiKeys' "
                    "AND column_name = 'uuid'"
                )
            )
        ).scalar_one_or_none()
        uuid_indexes = (
            await connection.execute(
                sa.text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE (schemaname = 'ApiKey' AND tablename = 'ApiKeys') "
                    "OR (schemaname = 'Billing' AND tablename = 'BillingTransactions')"
                )
            )
        ).fetchall()
    await engine.dispose()

    assert schemas == {
        "ApiKey",
        "Project",
        "Organization",
        "Billing",
        "Conversation",
        "FileStorage",
        "Rag",
    }
    assert api_key_uuid == "uuid"
    assert ("ApiKey", "ApiKeys", "uuid") in columns
    assert ("ApiKey", "ApiKeys", "hashed_key") in columns
    assert ("Project", "Projects", "uuid") in columns
    assert ("Billing", "BillingTransactions", "uuid") in columns
    assert ("Rag", "Metadata", "model_name") in columns
    assert uuid_indexes


@pytest.mark.asyncio
async def test_management_asyncpg_transaction_commit_and_rollback(
    migrated_management_storage,
    timescale_plain_uri: str,
) -> None:
    connection = await asyncpg.connect(timescale_plain_uri)
    try:
        await connection.execute(
            'CREATE TEMP TABLE integration_tx_check (id int PRIMARY KEY, value text)'
        )
        async with connection.transaction():
            await connection.execute(
                "INSERT INTO integration_tx_check VALUES (1, 'committed')"
            )
        committed = await connection.fetchval(
            "SELECT value FROM integration_tx_check WHERE id = 1"
        )

        with pytest.raises(RuntimeError):
            async with connection.transaction():
                await connection.execute(
                    "INSERT INTO integration_tx_check VALUES (2, 'rolled-back')"
                )
                raise RuntimeError("force rollback")
        rolled_back = await connection.fetchval(
            "SELECT value FROM integration_tx_check WHERE id = 2"
        )
    finally:
        await connection.close()

    assert committed == "committed"
    assert rolled_back is None


@pytest.mark.asyncio
async def test_management_cache_round_trip_ttl_and_delete_behavior(
    integration_config_file,
) -> None:
    getRedisConnectionPool.cache_clear()
    getRedis.cache_clear()
    cache_client = getRedis()
    await cache_client.set("gantry:integration", "ok", ex=30)
    value = await cache_client.get("gantry:integration")

    assert _decode(value) == "ok"
    await cache_client.set("gantry:integration:ttl", "ok", ex=30)
    ttl = await cache_client.ttl("gantry:integration:ttl")
    deleted = await cache_client.delete("gantry:integration:ttl")
    missing = await cache_client.get("gantry:integration:ttl")

    assert ttl > 0
    assert deleted == 1
    assert missing is None
    await cache_client.aclose()


@pytest.mark.asyncio
async def test_management_cache_text_and_binary_clients_have_expected_decode_behavior(
    integration_config_file,
) -> None:
    getRedisConnectionPool.cache_clear()
    getRedis.cache_clear()
    getRedisBinary.cache_clear()
    text_client = getRedis()
    binary_client = getRedisBinary()
    await text_client.set("gantry:integration:decode", "ok", ex=30)
    text_value = await text_client.get("gantry:integration:decode")
    binary_value = await binary_client.get("gantry:integration:decode")

    assert text_value == "ok"
    assert isinstance(binary_value, bytes)
    assert binary_value.decode() == "ok"
    await text_client.aclose()
    await binary_client.aclose()


@pytest.mark.asyncio
async def test_management_cache_repository_hit_miss_invalidate_and_get_or_call(
    integration_config_file,
) -> None:
    getRedisConnectionPool.cache_clear()
    getRedisBinary.cache_clear()
    cache_client = getRedisBinary()
    repo = RedisCacheRepository(cache_client, ttl=timedelta(seconds=30))
    key = "gantry:integration:repo"
    calls = 0

    await repo.invalidateCached(key)
    miss = await repo.getCached(key)

    async def loader() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"value": 1}

    first = await repo.getCachedOrCall(key, loader)
    second = await repo.getCachedOrCall(key, loader)
    hit = await repo.getCached(key)
    await repo.invalidateCached(key)
    after_delete = await repo.getCached(key)

    assert miss.status == ResultStatus.Err
    assert first == {"value": 1}
    assert second == {"value": 1}
    assert hit.unwrap() == {"value": 1}
    assert after_delete.status == ResultStatus.Err
    assert calls == 1
    await cache_client.aclose()
