import httpx
import pytest


BASE_URL = "http://localhost:8000"
KEYCLOAK_URL = "http://localhost:8080"
MAILPIT_URL = "http://localhost:8025"
REALM = "gantry"
CLIENT_ID = "gantry-frontend"

ORG_ID = "360dc549-8bfa-4ebd-9b57-983139c94af9"
ORG_NAME = "gantry-test-org"


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def org_id() -> str:
    return ORG_ID


def keycloak_login(username: str, password: str) -> dict:
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
    resp = httpx.post(
        token_url,
        data={
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "username": username,
            "password": password,
        },
    )
    resp.raise_for_status()
    return resp.json()


@pytest.fixture(scope="session")
def user1_token() -> str:
    data = keycloak_login("gantry-test-user", "password")
    return data["access_token"]


@pytest.fixture(scope="session")
def user1_client(user1_token: str, base_url: str) -> httpx.Client:
    return httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {user1_token}"},
        timeout=30,
    )
