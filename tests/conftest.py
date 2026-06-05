"""Root fixtures and test environment bootstrap."""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
import fakeredis.aioredis
from httpx import ASGITransport

from tests.factories import AdminInfoFactory, ApiKeyInfoFactory, UserInfoFactory
from tests.settings import REPO_ROOT, SRC_ROOT, config_file

sys.path.insert(0, str(SRC_ROOT))
os.environ.setdefault("GANTRY_SERVER__CONFIG_FILE", str(config_file()))


@pytest.fixture(scope="session")
def repo_root():
    return REPO_ROOT


@pytest.fixture(scope="session")
def management_app():
    from gantry.management import management_app

    return management_app


@pytest.fixture(scope="session")
def service_app():
    from gantry.service import service_app

    return service_app


@pytest.fixture(scope="session")
def gateway_app():
    from gantry.api_gateway.routes import gateway_app

    return gateway_app


@pytest.fixture(scope="session")
def internal_app():
    from gantry.main.app import internal_app

    return internal_app


@pytest.fixture(scope="session")
def management_openapi(management_app) -> dict:
    return management_app.openapi()


@pytest.fixture(scope="session")
def service_openapi(service_app) -> dict:
    return service_app.openapi()


@pytest.fixture(scope="session")
def gateway_openapi(gateway_app) -> dict:
    return gateway_app.openapi()


@pytest.fixture(scope="session")
def internal_openapi(internal_app) -> dict:
    return internal_app.openapi()


@pytest.fixture(scope="session")
def management_paths(management_openapi: dict) -> dict:
    return management_openapi["paths"]


@pytest.fixture(scope="session")
def service_paths(service_openapi: dict) -> dict:
    return service_openapi["paths"]


@pytest.fixture(scope="session")
def gateway_paths(gateway_openapi: dict) -> dict:
    return gateway_openapi["paths"]


@pytest.fixture(scope="session")
def internal_paths(internal_openapi: dict) -> dict:
    return internal_openapi["paths"]


@pytest.fixture
def fake_user_info() -> dict:
    return UserInfoFactory()


@pytest.fixture
def fake_admin_info() -> dict:
    return AdminInfoFactory()


@pytest.fixture
def fake_api_key_info() -> dict:
    return ApiKeyInfoFactory()


@pytest.fixture
async def fake_redis():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    try:
        yield redis
    finally:
        await redis.aclose()


@pytest.fixture
def override_dependencies(management_app) -> Iterator[dict]:
    original = dict(management_app.dependency_overrides)
    yield management_app.dependency_overrides
    management_app.dependency_overrides = original


@pytest.fixture
def service_override_dependencies(service_app) -> Iterator[dict]:
    original = dict(service_app.dependency_overrides)
    yield service_app.dependency_overrides
    service_app.dependency_overrides = original


@pytest.fixture
def gateway_override_dependencies(gateway_app) -> Iterator[dict]:
    original = dict(gateway_app.dependency_overrides)
    yield gateway_app.dependency_overrides
    gateway_app.dependency_overrides = original


@pytest.fixture
def internal_override_dependencies(internal_app) -> Iterator[dict]:
    original = dict(internal_app.dependency_overrides)
    yield internal_app.dependency_overrides
    internal_app.dependency_overrides = original


@pytest.fixture
async def api_client(management_app) -> AsyncIterator[httpx.AsyncClient]:
    transport = ASGITransport(app=management_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.fixture
async def service_client(service_app) -> AsyncIterator[httpx.AsyncClient]:
    transport = ASGITransport(app=service_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://service-testserver",
        follow_redirects=False,
    ) as client:
        yield client


@pytest.fixture
async def gateway_client(gateway_app) -> AsyncIterator[httpx.AsyncClient]:
    transport = ASGITransport(app=gateway_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://gateway-testserver",
    ) as client:
        yield client


@pytest.fixture
async def internal_client(internal_app) -> AsyncIterator[httpx.AsyncClient]:
    transport = ASGITransport(app=internal_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://internal-testserver",
    ) as client:
        yield client
