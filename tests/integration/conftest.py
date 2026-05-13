from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import asyncpg
import httpx
import pytest
from keycloak import KeycloakAdmin
from testcontainers.core.container import DockerContainer
from testcontainers.keycloak import KeycloakContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from tests.settings import REPO_ROOT, REALM


TIMESCALE_IMAGE = os.getenv(
    "GANTRY_INTEGRATION_TIMESCALE_IMAGE",
    "timescale/timescaledb:latest-pg18",
)
REDIS_IMAGE = os.getenv("GANTRY_INTEGRATION_REDIS_IMAGE", "redis:8-alpine")
KEYCLOAK_IMAGE = os.getenv(
    "GANTRY_INTEGRATION_KEYCLOAK_IMAGE",
    "quay.io/keycloak/keycloak:26.5.3",
)
MAILPIT_IMAGE = os.getenv(
    "GANTRY_INTEGRATION_MAILPIT_IMAGE",
    "axllent/mailpit:v1.29",
)
REQUIRE_FULL_STORAGE = os.getenv(
    "GANTRY_INTEGRATION_REQUIRE_FULL_STORAGE", ""
).lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class IntegrationStack:
    """Container-backed endpoints used by integration story tests."""

    timescale_asyncpg_uri: str
    timescale_plain_uri: str
    redis_url: str
    keycloak_url: str
    identity_metadata_url: str
    mailpit_smtp_url: tuple[str, int]
    email_messages_url: str


def wait_for_http_200(url: str, attempts: int = 90) -> None:
    for _ in range(attempts):
        try:
            response = httpx.get(url, timeout=8.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    raise RuntimeError(f"Timed out waiting for {url}")


def _require_docker() -> None:
    try:
        import docker

        docker.from_env().ping()
    except Exception as exc:
        pytest.skip(f"Docker is required for integration tests: {exc}")


def _clear_gantry_caches() -> None:
    from gantry.settings import AppSettings
    from gantry.db import factories as db_factories
    from gantry.keycloak import factories as keycloak_factories
    from gantry.management.auth import factories as auth_factories
    from gantry.management.api_key import factories as api_key_factories
    from gantry.management.organization import factories as org_factories
    from gantry.management.project import factories as project_factories
    from gantry.management.billing import factories as billing_factories
    from gantry.management.admin import factories as admin_factories

    AppSettings._setInstance(None)
    for maybe_cached in [
        db_factories.getAsyncEngine,
        db_factories.getSessionManager,
        db_factories.getRedisConnectionPool,
        db_factories.getRedisTextConnectionPool,
        db_factories.getRedis,
        db_factories.getRedisBinary,
        db_factories.getRedisCacheRepo,
        keycloak_factories.getKeycloakServiceClient,
        auth_factories.getAuthService,
        auth_factories.getAdminAuthService,
        api_key_factories.getApiKeyRepository,
        api_key_factories.getApiKeyService,
        org_factories.getOrgSettingsRepository,
        org_factories.getOrgService,
        project_factories.getProjectRepository,
        project_factories.getProjectMemeberRepository,
        project_factories.getProjectSettingsRepository,
        project_factories.getProjectService,
        billing_factories.getBillingSourceService,
        billing_factories.getStripeClient,
        billing_factories.getCreditService,
        billing_factories.getInvoiceService,
        billing_factories.getBillingTransactionService,
        billing_factories.getBillingAggregateQueryService,
        admin_factories.getAdminService,
    ]:
        maybe_cached.cache_clear()


@pytest.fixture(scope="session")
def timescale_container() -> Iterator[PostgresContainer]:
    _require_docker()
    container = PostgresContainer(
        TIMESCALE_IMAGE,
        username="gantry",
        password="123456",
        dbname="gantry",
        driver="asyncpg",
    )
    with container:
        yield container


@pytest.fixture(scope="session")
def redis_container() -> Iterator[RedisContainer]:
    _require_docker()
    container = RedisContainer(REDIS_IMAGE)
    with container:
        yield container


@pytest.fixture(scope="session")
def keycloak_container() -> Iterator[KeycloakContainer]:
    _require_docker()
    realm_file = REPO_ROOT / "asset" / "gantry-realm.json"
    container = KeycloakContainer(
        KEYCLOAK_IMAGE,
        username="admin",
        password="admin",
        cmd="start-dev --http-access-log-enabled=true --health-enabled=true",
    ).with_realm_import_file(str(realm_file))
    with container:
        wait_for_http_200(
            f"{container.get_url()}/realms/{REALM}/.well-known/openid-configuration"
        )
        yield container


@pytest.fixture(scope="session")
def mailpit_container() -> Iterator[DockerContainer]:
    _require_docker()
    container = DockerContainer(MAILPIT_IMAGE).with_exposed_ports(1025, 8025)
    with container:
        wait_for_http_200(
            f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8025)}/api/v1/messages"
        )
        yield container


@pytest.fixture(scope="session")
def timescale_asyncpg_uri(timescale_container: PostgresContainer) -> str:
    return timescale_container.get_connection_url(driver="asyncpg")


@pytest.fixture(scope="session")
def timescale_plain_uri(timescale_container: PostgresContainer) -> str:
    return timescale_container.get_connection_url(driver=None)


@pytest.fixture(scope="session")
def redis_url(redis_container: RedisContainer) -> str:
    return (
        f"redis://{redis_container.get_container_host_ip()}:"
        f"{redis_container.get_exposed_port(6379)}/0"
    )


@pytest.fixture(scope="session")
def keycloak_url(keycloak_container: KeycloakContainer) -> str:
    return keycloak_container.get_url()


@pytest.fixture(scope="session")
def mailpit_smtp_url(mailpit_container: DockerContainer) -> tuple[str, int]:
    return (
        mailpit_container.get_container_host_ip(),
        int(mailpit_container.get_exposed_port(1025)),
    )


@pytest.fixture(scope="session")
def email_messages_url(mailpit_container: DockerContainer) -> str:
    return (
        f"http://{mailpit_container.get_container_host_ip()}:"
        f"{mailpit_container.get_exposed_port(8025)}/api/v1/messages"
    )


@pytest.fixture(scope="session")
def integration_stack(
    timescale_asyncpg_uri: str,
    timescale_plain_uri: str,
    redis_url: str,
    keycloak_url: str,
    mailpit_smtp_url: tuple[str, int],
    email_messages_url: str,
) -> IntegrationStack:
    return IntegrationStack(
        timescale_asyncpg_uri=timescale_asyncpg_uri,
        timescale_plain_uri=timescale_plain_uri,
        redis_url=redis_url,
        keycloak_url=keycloak_url,
        identity_metadata_url=(
            f"{keycloak_url}/realms/{REALM}/.well-known/openid-configuration"
        ),
        mailpit_smtp_url=mailpit_smtp_url,
        email_messages_url=email_messages_url,
    )


@pytest.fixture(scope="session")
def integration_config_file(
    tmp_path_factory: pytest.TempPathFactory,
    timescale_asyncpg_uri: str,
    redis_url: str,
    keycloak_url: str,
) -> Path:
    config_path = tmp_path_factory.mktemp("gantry-integration") / "gantry.integration.toml"
    content = (REPO_ROOT / "example.gantry.toml").read_text()
    replacements = {
        'timescale_connection_uri = "postgresql+asyncpg://gantry:123456@localhost:5432/gantry"': f'timescale_connection_uri = "{timescale_asyncpg_uri}"',
        'pgvector_connection_uri = "postgresql+asyncpg://gantry:123456@localhost:5432/gantry"': f'pgvector_connection_uri = "{timescale_asyncpg_uri}"',
        'redis_connection_uri = "redis://localhost:6379/0"': f'redis_connection_uri = "{redis_url}"',
        'server_url = "http://localhost:8080/"': f'server_url = "{keycloak_url}/"',
    }
    for old, new in replacements.items():
        content = content.replace(old, new)
    config_path.write_text(content)

    previous_config = os.environ.get("GANTRY_SERVER__CONFIG_FILE")
    previous_keycloak = os.environ.get("KEYCLOAK_URL")
    previous_mailpit = os.environ.get("MAILPIT_API_URL")
    os.environ["GANTRY_SERVER__CONFIG_FILE"] = str(config_path)
    os.environ["KEYCLOAK_URL"] = keycloak_url
    _clear_gantry_caches()
    try:
        yield config_path
    finally:
        if previous_config is None:
            os.environ.pop("GANTRY_SERVER__CONFIG_FILE", None)
        else:
            os.environ["GANTRY_SERVER__CONFIG_FILE"] = previous_config
        if previous_keycloak is None:
            os.environ.pop("KEYCLOAK_URL", None)
        else:
            os.environ["KEYCLOAK_URL"] = previous_keycloak
        if previous_mailpit is None:
            os.environ.pop("MAILPIT_API_URL", None)
        else:
            os.environ["MAILPIT_API_URL"] = previous_mailpit
        _clear_gantry_caches()


async def _create_required_extensions(connection_uri: str) -> None:
    connection = await asyncpg.connect(connection_uri)
    try:
        await connection.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
        await connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
    finally:
        await connection.close()


@pytest.fixture(scope="session")
def migrated_management_storage(
    integration_config_file: Path,
    timescale_plain_uri: str,
) -> Path:
    try:
        import asyncio

        asyncio.run(_create_required_extensions(timescale_plain_uri))
    except Exception as exc:
        if REQUIRE_FULL_STORAGE:
            raise
        pytest.skip(
            "Integration storage image does not support required "
            f"timescaledb/vector extensions: {exc}"
        )

    subprocess.run(
        ["uv", "run", "gantry", "server", "-f", str(integration_config_file), "migrate"],
        cwd=REPO_ROOT,
        check=True,
        timeout=240,
    )
    return integration_config_file


@pytest.fixture(scope="session")
def migrated_management_storage_twice(
    migrated_management_storage: Path,
) -> Path:
    subprocess.run(
        ["uv", "run", "gantry", "server", "-f", str(migrated_management_storage), "migrate"],
        cwd=REPO_ROOT,
        check=True,
        timeout=240,
    )
    return migrated_management_storage


@pytest.fixture(scope="session")
def identity_metadata_url(keycloak_url: str) -> str:
    return f"{keycloak_url}/realms/{REALM}/.well-known/openid-configuration"


@pytest.fixture(scope="session")
def keycloak_admin_client(keycloak_container: KeycloakContainer) -> KeycloakAdmin:
    return KeycloakAdmin(
        server_url=f"{keycloak_container.get_url()}/",
        username="admin",
        password="admin",
        realm_name=REALM,
        user_realm_name="master",
        verify=True,
    )


@pytest.fixture(scope="session")
def public_management_url() -> str:
    return "http://testserver/management/v1/organizations/permissions"


@pytest.fixture(autouse=True)
async def reset_gantry_singletons_after_integration_test() -> Iterator[None]:
    yield

    from gantry.db import factories as db_factories

    if db_factories.getRedis.cache_info().currsize:
        await db_factories.getRedis().aclose()
    if db_factories.getRedisBinary.cache_info().currsize:
        await db_factories.getRedisBinary().aclose()
    if db_factories.getAsyncEngine.cache_info().currsize:
        await db_factories.getAsyncEngine().dispose()
    _clear_gantry_caches()
