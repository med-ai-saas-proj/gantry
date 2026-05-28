from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from uuid import uuid4

import httpx
import pytest
from playwright.sync_api import APIRequestContext, APIResponse, Playwright

from tests.helpers.auth import bearer, password_token, token_claims
from tests.settings import BASE_URL, KEYCLOAK_URL, MAILPIT_API_URL, REALM, REPO_ROOT


SEEDED_USER_USERNAME = os.environ.get("E2E_SEEDED_USER_USERNAME", "gantry-test-user")
SEEDED_ADMIN_USERNAME = os.environ.get("E2E_SEEDED_ADMIN_USERNAME", "gantry-admin-user")
SEEDED_PASSWORD = os.environ.get("E2E_SEEDED_PASSWORD", "password")
FRONTEND_CLIENT_ID = os.environ.get("E2E_FRONTEND_CLIENT_ID", "gantry-frontend")
ADMIN_CLIENT_ID = os.environ.get("E2E_ADMIN_CLIENT_ID", "gantry-admin")
KEYCLOAK_ADMIN_USERNAME = os.environ.get("KEYCLOAK_ADMIN_USERNAME", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "admin")
MINIO_URL = os.environ.get("MINIO_URL", "http://localhost:9000")


@dataclass(frozen=True)
class E2EOrg:
    org_id: str
    name: str
    settings: dict


@dataclass
class BackendE2EContext:
    base_url: str
    keycloak_url: str
    mailpit_url: str
    realm: str
    org_id: str
    org_name: str
    created_projects: list[str] = field(default_factory=list)
    created_api_keys: list[str] = field(default_factory=list)


class BackendAPIResponse:
    """Small compatibility wrapper around Playwright's APIResponse."""

    def __init__(self, response: APIResponse):
        self._response = response
        self.status_code = response.status

    @property
    def text(self) -> str:
        return self._response.text()

    def json(self):
        return self._response.json()


class BackendE2EClient:
    def __init__(self, context: BackendE2EContext, api_context: APIRequestContext):
        self.context = context
        self.api_context = api_context
        self._admin_token: str | None = None
        self._user_token: str | None = None

    def close(self) -> None:
        self.cleanup_created_resources()

    @property
    def admin_headers(self) -> dict[str, str]:
        if self._admin_token is None:
            token = password_token(
                SEEDED_ADMIN_USERNAME,
                SEEDED_PASSWORD,
                ADMIN_CLIENT_ID,
                keycloak_url=self.context.keycloak_url,
                realm=self.context.realm,
            )
            self._admin_token = token["access_token"]
        return bearer(self._admin_token)

    @property
    def user_headers(self) -> dict[str, str]:
        if self._user_token is None:
            # Request the token in the context of the fresh organization created
            # for this E2E run. This should make Keycloak emit the organization
            # claim; AuthService still has a membership fallback as a safety net.
            token = password_token(
                SEEDED_USER_USERNAME,
                SEEDED_PASSWORD,
                FRONTEND_CLIENT_ID,
                scope=f"openid profile email organization:{self.context.org_name}",
                keycloak_url=self.context.keycloak_url,
                realm=self.context.realm,
            )
            self._user_token = token["access_token"]
        return bearer(self._user_token)

    def user_token_claims(self) -> dict:
        _ = self.user_headers
        assert self._user_token is not None
        return token_claims(self._user_token)

    def refresh_user_token(self) -> None:
        self._user_token = None

    def request(self, method: str, path: str, **kwargs) -> BackendAPIResponse:
        headers = kwargs.pop("headers", None)
        params = kwargs.pop("params", None)
        json_payload = kwargs.pop("json", None)
        data = kwargs.pop("data", None)
        if kwargs:
            raise TypeError(f"Unsupported Playwright E2E request kwargs: {sorted(kwargs)}")

        request_data = json_payload if json_payload is not None else data
        response = self.api_context.fetch(
            path,
            method=method,
            headers=headers,
            params=params,
            data=request_data,
            timeout=20_000,
        )
        return BackendAPIResponse(response)

    def admin_request(self, method: str, path: str, **kwargs) -> BackendAPIResponse:
        headers = {**self.admin_headers, **kwargs.pop("headers", {})}
        return self.request(method, path, headers=headers, **kwargs)

    def user_request(self, method: str, path: str, **kwargs) -> BackendAPIResponse:
        headers = {**self.user_headers, **kwargs.pop("headers", {})}
        return self.request(method, path, headers=headers, **kwargs)

    def mailpit_messages(self) -> dict:
        response = self.request("GET", f"{self.context.mailpit_url.rstrip('/')}/api/v1/messages")
        assert response.status_code == 200, response.text
        return response.json()

    def find_user_id(self, username: str) -> str:
        response = self.admin_request("GET", "/management/v1/admin/users", params={"q": username})
        assert response.status_code == 200, response.text
        for user in response.json().get("results", []):
            if user.get("username") == username:
                return user.get("user_id") or user["id"]
        raise AssertionError(f"Could not find seeded user {username!r}: {response.text}")

    def create_project(self, *, name_prefix: str = "e2e-backend") -> dict:
        response = self.admin_request(
            "POST",
            "/management/v1/admin/projects",
            params={"org_id": self.context.org_id},
            json={
                "name": f"{name_prefix}-{uuid4()}",
                "description": "backend-first e2e project",
            },
        )
        assert response.status_code == 201, response.text
        project = response.json()
        self.context.created_projects.append(project["project_uuid"])
        return project

    def create_api_key(self, project_uuid: str, permissions: list[str] | None = None) -> dict:
        response = self.admin_request(
            "POST",
            "/management/v1/admin/api-keys",
            params={"project_id": project_uuid},
            json={
                "name": f"e2e-key-{uuid4()}",
                "description": "backend-first e2e api key",
                "permissions": permissions or ["chat.read", "conversation.read"],
            },
        )
        assert response.status_code == 201, response.text
        api_key = response.json()
        self.context.created_api_keys.append(api_key["api_key_uuid"])
        return api_key

    def cleanup_created_resources(self) -> None:
        for api_key_uuid in reversed(self.context.created_api_keys):
            try:
                self.admin_request("DELETE", f"/management/v1/admin/api-keys/{api_key_uuid}")
            except Exception:
                pass
        self.context.created_api_keys.clear()

        for project_uuid in reversed(self.context.created_projects):
            try:
                self.admin_request("DELETE", f"/management/v1/admin/projects/{project_uuid}")
            except Exception:
                pass
        self.context.created_projects.clear()


def _http_status_ready(url: str, expected: set[int] | None = None) -> bool:
    expected = expected or {200}
    try:
        response = httpx.get(url, timeout=8.0)
    except httpx.HTTPError:
        return False
    return response.status_code in expected


def _container_running(name: str) -> bool:
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", name],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _existing_infra_ready() -> bool:
    return (
        _container_running("timescale-db")
        and _container_running("redis")
        and _container_running("keycloak")
        and _container_running("mailpit")
        and _container_running("minio")
    )


def _compose_network_gateway() -> str | None:
    result = subprocess.run(
        [
            "docker",
            "network",
            "inspect",
            "med-ai-saas_default",
            "--format",
            "{{(index .IPAM.Config 0).Gateway}}",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    gateway = result.stdout.strip()
    if result.returncode == 0 and gateway:
        return gateway
    return None


def _wait_for_http_status(url: str, expected: set[int] | None = None, attempts: int = 90) -> None:
    expected = expected or {200}
    for _ in range(attempts):
        if _http_status_ready(url, expected):
            return
        time.sleep(2)
    _dump_compose_diagnostics()
    raise RuntimeError(f"Timed out waiting for {url}")


def _dump_compose_diagnostics() -> None:
    """Print compose diagnostics so CI logs show why stack readiness failed."""
    commands = [
        ["docker", "compose", "-f", "compose.yaml", "-f", "docker/docker-compose.e2e.yml", "ps", "-a"],
        ["docker", "compose", "-f", "compose.yaml", "-f", "docker/docker-compose.e2e.yml", "logs", "--no-color", "--tail=200", "gantry"],
    ]
    for command in commands:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        print(f"$ {' '.join(command)}")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)


def _compose_up() -> list[str]:
    infra_was_ready = (
        os.environ.get("E2E_FORCE_COMPOSE") != "1"
        and _existing_infra_ready()
    )
    services = ["gantry"] if infra_was_ready else [
        "timescale_db",
        "redis",
        "keycloak",
        "mailpit",
        "minio",
        "gantry",
    ]
    try:
        up_command = [
            "docker",
            "compose",
            "-f",
            "compose.yaml",
            "-f",
            "docker/docker-compose.e2e.yml",
            "up",
            "-d",
            "--build",
        ]
        if infra_was_ready:
            up_command.append("--no-deps")
        up_command.extend(services)
        env = os.environ.copy()
        if infra_was_ready:
            gateway = _compose_network_gateway() or "host.docker.internal"
            env.setdefault("E2E_GANTRY_DB_HOST", gateway)
            env.setdefault("E2E_GANTRY_REDIS_HOST", gateway)
            env.setdefault("E2E_GANTRY_KEYCLOAK_URL", f"http://{gateway}:8080/")
            env.setdefault("E2E_GANTRY_S3_ENDPOINT_URL", f"http://{gateway}:9000")
        subprocess.run(
            up_command,
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
    except subprocess.CalledProcessError:
        if _existing_infra_ready() and _http_status_ready(
            f"{BASE_URL}/management/v1/organizations/permissions"
        ):
            return []
        raise
    return ["gantry"] if infra_was_ready else services


def _compose_down(started_services: list[str]) -> None:
    if started_services == ["gantry"]:
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "compose.yaml",
                "-f",
                "docker/docker-compose.e2e.yml",
                "rm",
                "-sf",
                "gantry",
            ],
            cwd=REPO_ROOT,
            check=False,
        )
        return
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "compose.yaml",
            "-f",
            "docker/docker-compose.e2e.yml",
            "down",
        ],
        cwd=REPO_ROOT,
        check=False,
    )


@pytest.fixture(scope="session")
def full_stack() -> Iterator[dict[str, str]]:
    started_services: list[str] = []
    if os.environ.get("E2E_SKIP_COMPOSE") != "1":
        started_services = _compose_up()

    _wait_for_http_status(f"{KEYCLOAK_URL}/realms/{REALM}/.well-known/openid-configuration")
    _wait_for_http_status(f"{BASE_URL}/management/v1/organizations/permissions")
    _wait_for_http_status(f"{MAILPIT_API_URL.rstrip('/')}/api/v1/messages")
    _wait_for_http_status(f"{MINIO_URL.rstrip('/')}/minio/health/live")

    yield {
        "base_url": BASE_URL.rstrip("/"),
        "keycloak_url": KEYCLOAK_URL.rstrip("/"),
        "mailpit_url": MAILPIT_API_URL.rstrip("/"),
        "realm": REALM,
    }

    if os.environ.get("E2E_SKIP_COMPOSE") != "1" and os.environ.get("E2E_KEEP_STACK") != "1":
        _compose_down(started_services)


@pytest.fixture(scope="session")
def playwright_backend_context(
    full_stack: dict[str, str],
    playwright: Playwright,
) -> Iterator[APIRequestContext]:
    context = playwright.request.new_context(
        base_url=full_stack["base_url"],
        timeout=20_000,
    )
    yield context
    context.dispose()


def _admin_headers(keycloak_url: str, realm: str) -> dict[str, str]:
    token = password_token(
        SEEDED_ADMIN_USERNAME,
        SEEDED_PASSWORD,
        ADMIN_CLIENT_ID,
        keycloak_url=keycloak_url,
        realm=realm,
    )
    return bearer(token["access_token"])


def _keycloak_admin_headers(keycloak_url: str) -> dict[str, str]:
    response = httpx.post(
        f"{keycloak_url}/realms/master/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "username": KEYCLOAK_ADMIN_USERNAME,
            "password": KEYCLOAK_ADMIN_PASSWORD,
            "grant_type": "password",
        },
        timeout=20.0,
    )
    response.raise_for_status()
    return bearer(response.json()["access_token"])


def _remove_user_from_keycloak_orgs(
    keycloak_url: str,
    user_id: str,
) -> None:
    headers = _keycloak_admin_headers(keycloak_url)
    response = httpx.get(
        f"{keycloak_url}/admin/realms/{REALM}/organizations/members/{user_id}/organizations",
        headers=headers,
        timeout=20.0,
    )
    if response.status_code != 200:
        return

    for org in response.json():
        org_id = org.get("id")
        if not org_id:
            continue
        httpx.delete(
            f"{keycloak_url}/admin/realms/{REALM}/organizations/{org_id}/members/{user_id}",
            headers=headers,
            timeout=20.0,
        )


def _delete_keycloak_org(keycloak_url: str, org_id: str) -> None:
    headers = _keycloak_admin_headers(keycloak_url)
    httpx.delete(
        f"{keycloak_url}/admin/realms/{REALM}/organizations/{org_id}",
        headers=headers,
        timeout=20.0,
    )


def _fetch(
    api_context: APIRequestContext,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict | None = None,
    json: dict | None = None,
) -> BackendAPIResponse:
    return BackendAPIResponse(
        api_context.fetch(
            path,
            method=method,
            headers=headers,
            params=params,
            data=json,
            timeout=20_000,
        )
    )


def _find_seeded_user_id(
    api_context: APIRequestContext,
    admin_headers: dict[str, str],
) -> str:
    response = _fetch(
        api_context,
        "GET",
        "/management/v1/admin/users",
        headers=admin_headers,
        params={"q": SEEDED_USER_USERNAME},
    )
    assert response.status_code == 200, response.text
    for user in response.json().get("results", []):
        if user.get("username") == SEEDED_USER_USERNAME:
            return user.get("user_id") or user["id"]
    raise AssertionError(f"Could not find seeded user {SEEDED_USER_USERNAME!r}: {response.text}")


@pytest.fixture(scope="session")
def e2e_org(
    full_stack: dict[str, str],
    playwright_backend_context: APIRequestContext,
) -> Iterator[E2EOrg]:
    admin_headers = _admin_headers(full_stack["keycloak_url"], full_stack["realm"])
    owner_id = _find_seeded_user_id(playwright_backend_context, admin_headers)
    _remove_user_from_keycloak_orgs(full_stack["keycloak_url"], owner_id)
    suffix = uuid4().hex[:12]
    org_name = f"e2e-backend-{suffix}"
    create = _fetch(
        playwright_backend_context,
        "POST",
        "/management/v1/admin/organizations",
        headers=admin_headers,
        json={"name": org_name, "alias": org_name, "owner_id": owner_id},
    )
    assert create.status_code == 201, create.text
    org_id = create.json()["org_id"]

    settings_payload = {
        "rate_limit": 1200,
        "spending_limit": None,
        "extra": {"e2e": "backend", "created_by": "playwright"},
    }
    settings = _fetch(
        playwright_backend_context,
        "PATCH",
        f"/management/v1/admin/organizations/{org_id}/settings",
        headers=admin_headers,
        json=settings_payload,
    )
    assert settings.status_code == 200, settings.text

    yield E2EOrg(org_id=org_id, name=org_name, settings=settings.json())

    try:
        _fetch(
            playwright_backend_context,
            "DELETE",
            f"/management/v1/admin/organizations/{org_id}",
            headers=admin_headers,
        )
    except Exception:
        pass
    try:
        _remove_user_from_keycloak_orgs(full_stack["keycloak_url"], owner_id)
        _delete_keycloak_org(full_stack["keycloak_url"], org_id)
    except Exception:
        pass


@pytest.fixture()
def backend_e2e(
    full_stack: dict[str, str],
    e2e_org: E2EOrg,
    playwright_backend_context: APIRequestContext,
) -> Iterator[BackendE2EClient]:
    context = BackendE2EContext(
        base_url=full_stack["base_url"],
        keycloak_url=full_stack["keycloak_url"],
        mailpit_url=full_stack["mailpit_url"],
        realm=full_stack["realm"],
        org_id=e2e_org.org_id,
        org_name=e2e_org.name,
    )
    client = BackendE2EClient(context, playwright_backend_context)
    yield client
    client.close()
