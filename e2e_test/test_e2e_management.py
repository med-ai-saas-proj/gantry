"""End-to-end tests for the Gantry management API.

Tests organization operations, user invitations, permission enforcement,
API key lifecycle, and project-level permissions using a running server.
"""

import re
import time

import html

import httpx
import pytest
from playwright.sync_api import sync_playwright

from conftest import (
    BASE_URL,
    CLIENT_ID,
    KEYCLOAK_URL,
    MAILPIT_URL,
    ORG_ID,
    REALM,
    keycloak_login,
)

MGMT = "/management/v1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def mgmt_url(path: str) -> str:
    return f"{MGMT}{path}"


def org_url(path: str = "") -> str:
    return mgmt_url(f"/organizations/{ORG_ID}{path}")


def signup_user_via_mailpit(email: str, password: str = "password") -> str:
    """Check mailpit for the invitation email, extract signup link,
    complete registration via Playwright, and return the new user's
    access token.
    """
    time.sleep(2)
    username = email.split("@")[0]

    resp = httpx.get(
        f"{MAILPIT_URL}/api/v1/search",
        params={"query": f"to:{email}"},
        timeout=15,
    )
    resp.raise_for_status()
    messages = resp.json().get("messages", [])
    assert len(messages) > 0, f"No invitation email found for {email}"

    msg_id = messages[0]["ID"]
    msg_resp = httpx.get(
        f"{MAILPIT_URL}/api/v1/message/{msg_id}",
        timeout=15,
    )
    msg_resp.raise_for_status()
    msg_data = msg_resp.json()

    body = msg_data.get("Text", "") or msg_data.get("HTML", "")
    link_match = re.search(r"https?://[^\s\"<>]+", body)
    assert link_match, f"No signup link found in email body for {email}"
    signup_link = link_match.group(0)
    signup_link = html.unescape(signup_link)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(signup_link)
        page.wait_for_load_state("networkidle")
        page.locator("#username").fill(username)
        page.locator("#password").fill(password)
        page.locator("#password-confirm").fill(password)
        page.locator("#email").fill(email)
        page.locator("#firstName").fill(username)
        page.locator("#lastName").fill("test")

        page.locator("input[type='submit'], button[type='submit']").click()
        page.wait_for_load_state("networkidle")

        browser.close()

    token_data = keycloak_login(username, password)
    return token_data["access_token"]


def make_client(token: str) -> httpx.Client:
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )


# ---------------------------------------------------------------------------
# 2. BASELINE ORGANIZATION OPS (User1)
# ---------------------------------------------------------------------------


class TestBaselineOrgOps:
    """Section 2: Basic org operations as User1 (owner)."""

    def test_get_org_settings(self, user1_client: httpx.Client):
        resp = user1_client.get(org_url("/settings"))
        assert resp.status_code == 200
        data = resp.json()
        assert "rate_limit" in data

    def test_create_and_manage_projects(
        self, user1_client: httpx.Client, org_id: str
    ):
        # Create Project A
        resp = user1_client.post(
            mgmt_url("/projects"),
            params={"organization": org_id},
            json={"name": "Project A", "description": "Test project A"},
        )
        assert resp.status_code == 201
        project_a = resp.json()
        project_a_id = project_a["project_uuid"]

        # Create Project C
        resp = user1_client.post(
            mgmt_url("/projects"),
            params={"organization": org_id},
            json={"name": "Project C", "description": "Test project C"},
        )
        assert resp.status_code == 201
        project_c = resp.json()
        project_c_id = project_c["project_uuid"]

        # Delete Project C
        resp = user1_client.post(
            mgmt_url(f"/projects/{project_c_id}/archive"),
        )
        assert resp.status_code == 200

        # Rename Project A -> Project D
        resp = user1_client.put(
            mgmt_url(f"/projects/{project_a_id}"),
            json={"name": "Project D", "description": "Renamed project"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Project D"

        # Store for later tests
        pytest.project_d_id = project_a_id


# ---------------------------------------------------------------------------
# 3. INVITE USER2 & VERIFY RESTRICTIONS
# ---------------------------------------------------------------------------


class TestInviteUser2Restrictions:
    """Section 3: Invite User2 with no permissions, verify 403s."""

    @pytest.fixture(autouse=True, scope="class")
    def setup_user2(self, user1_client: httpx.Client):
        # Invite user2
        # input("FUCK")
        resp = user1_client.post(
            org_url("/invitations"),
            json={"email": "test-user2@gantry.com"},
        )
        # print(resp.status_code)
        # input("Check mail")
        assert resp.status_code == 200

        # Sign up user2 via mailpit
        token = signup_user_via_mailpit("test-user2@gantry.com")
        pytest.user2_token = token
        pytest.user2_client = make_client(token)

    def test_list_users_forbidden(self):
        resp = pytest.user2_client.get(org_url("/users"))
        assert resp.status_code == 403

    def test_remove_user_forbidden(self):
        resp = pytest.user2_client.delete(org_url("/users/some-user-id"))
        assert resp.status_code == 403

    def test_get_settings_forbidden(self):
        resp = pytest.user2_client.get(org_url("/settings"))
        assert resp.status_code == 403

    def test_patch_settings_forbidden(self):
        resp = pytest.user2_client.patch(
            org_url("/settings"),
            json={"rate_limit": 100, "spending_limit": None, "extra": {}},
        )
        assert resp.status_code == 403

    def test_get_billing_forbidden(self):
        resp = pytest.user2_client.get(
            mgmt_url("/billing/aggregates/organizations"),
            params={
                "period_start": "2024-01-01T00:00:00Z",
                "period_end": "2024-12-31T00:00:00Z",
                "period": "monthly",
            },
        )
        assert resp.status_code == 403

    def test_get_invitations_forbidden(self):
        resp = pytest.user2_client.get(org_url("/invitations"))
        assert resp.status_code == 403

    def test_get_own_permissions_allowed(self):
        token_data = keycloak_login("test-user2", "password")
        # We need the user's own ID from the token
        import jwt as pyjwt

        payload = pyjwt.decode(
            token_data["access_token"],
            options={"verify_signature": False},
        )
        user2_id = payload["sub"]
        pytest.user2_id = user2_id

        resp = pytest.user2_client.get(
            org_url(f"/users/{user2_id}/permissions")
        )
        assert resp.status_code == 200

    def test_change_own_permissions_forbidden(self):
        resp = pytest.user2_client.put(
            org_url(f"/users/{pytest.user2_id}/permissions"),
            json={"permissions": ["organization.owner"]},
        )
        assert resp.status_code == 403

    def test_list_projects_forbidden(self):
        resp = pytest.user2_client.get(
            mgmt_url("/projects"),
            params={"organization": ORG_ID},
        )
        assert resp.status_code == 403

    def test_create_project_forbidden(self):
        resp = pytest.user2_client.post(
            mgmt_url("/projects"),
            params={"organization": ORG_ID},
            json={"name": "Forbidden Project"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 4. GRANT ORG PERMISSIONS (User1 -> User2)
# ---------------------------------------------------------------------------


class TestGrantOrgPermissions:
    """Section 4: User1 grants org permissions to User2."""

    def test_grant_project_permissions(self, user1_client: httpx.Client):
        resp = user1_client.put(
            org_url(f"/users/{pytest.user2_id}/permissions"),
            json={
                "permissions": [
                    "organization.projects.create",
                    "organization.projects.get_all",
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "organization.projects.create" in data["permissions"]
        assert "organization.projects.get_all" in data["permissions"]


# ---------------------------------------------------------------------------
# 5. VERIFY GRANTED ORG PERMISSIONS (User2)
# ---------------------------------------------------------------------------


class TestVerifyGrantedPermissions:
    """Section 5: User2 exercises newly granted permissions."""

    @pytest.fixture(autouse=True, scope="class")
    def refresh_user2_token(self):
        token = keycloak_login("test-user2", "password")["access_token"]
        pytest.user2_client = make_client(token)
        pytest.user2_token = token

    def test_list_projects_succeeds(self):
        resp = pytest.user2_client.get(
            mgmt_url("/projects"),
            params={"organization": ORG_ID},
        )
        assert resp.status_code == 200
        data = resp.json()
        project_names = [p["name"] for p in data["results"]]
        assert "Project D" in project_names

    def test_create_project_e(self):
        resp = pytest.user2_client.post(
            mgmt_url("/projects"),
            params={"organization": ORG_ID},
            json={"name": "Project E", "description": "User2's project"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Project E"
        pytest.project_e_id = data["project_uuid"]


# ---------------------------------------------------------------------------
# 6. API-KEY LIFECYCLE (User2 on Project E)
# ---------------------------------------------------------------------------


class TestApiKeyLifecycle:
    """Section 6: Full API key CRUD on Project E by User2 (owner)."""

    @pytest.fixture(autouse=True, scope="class")
    def refresh_user2_token(self):
        token = keycloak_login("test-user2", "password")["access_token"]
        pytest.user2_client = make_client(token)

    def test_list_keys_empty(self):
        resp = pytest.user2_client.get(
            mgmt_url("/api-keys"),
            params={"project_id": pytest.project_e_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["results"] == []

    def test_create_key(self):
        resp = pytest.user2_client.post(
            mgmt_url("/api-keys"),
            params={"project_id": pytest.project_e_id},
            json={
                "name": "Test Key",
                "description": "E2E test key",
                "permissions": ["chat.read", "chat.run"],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "key" in data
        assert data["name"] == "Test Key"
        pytest.api_key_uuid = data["api_key_uuid"]

    def test_list_keys_has_one(self):
        resp = pytest.user2_client.get(
            mgmt_url("/api-keys"),
            params={"project_id": pytest.project_e_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_get_key_by_uuid(self):
        resp = pytest.user2_client.get(
            mgmt_url(f"/api-keys/{pytest.api_key_uuid}"),
        )
        assert resp.status_code == 200
        assert resp.json()["api_key_uuid"] == pytest.api_key_uuid

    def test_update_key(self):
        resp = pytest.user2_client.put(
            mgmt_url(f"/api-keys/{pytest.api_key_uuid}"),
            json={
                "name": "Updated Key",
                "description": "Updated description",
                "permissions": ["chat.read"],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Key"

    def test_delete_key(self):
        resp = pytest.user2_client.delete(
            mgmt_url(f"/api-keys/{pytest.api_key_uuid}"),
        )
        assert resp.status_code == 200

    def test_verify_deletion(self):
        resp = pytest.user2_client.get(
            mgmt_url(f"/api-keys/{pytest.api_key_uuid}"),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 7. PROJECT-LEVEL PERMISSION TESTING (User3)
# ---------------------------------------------------------------------------


class TestProjectPermissions:
    """Section 7: User3 with limited project permissions on Project E."""

    @pytest.fixture(autouse=True, scope="class")
    def setup_user3(self, user1_client: httpx.Client):
        # User1 invites user3
        resp = user1_client.post(
            org_url("/invitations"),
            json={"email": "test-user3@gantry.com"},
        )
        assert resp.status_code == 200

        # Sign up user3
        token = signup_user_via_mailpit("test-user3@gantry.com")
        pytest.user3_token = token

        import jwt as pyjwt

        payload = pyjwt.decode(token, options={"verify_signature": False})
        pytest.user3_id = payload["sub"]

        # User2 adds User3 to Project E with limited permissions
        user2_token = keycloak_login("test-user2", "password")["access_token"]
        user2_client = make_client(user2_token)

        # Add user3 to project
        resp = user2_client.post(
            mgmt_url(f"/projects/{pytest.project_e_id}/users"),
            json={"user_id": pytest.user3_id},
        )
        assert resp.status_code == 200

        # Set user3 permissions on project E
        resp = user2_client.put(
            mgmt_url(
                f"/projects/{pytest.project_e_id}"
                f"/users/{pytest.user3_id}/permissions"
            ),
            json={
                "permissions": [
                    "project.member",
                    "project.settings.read",
                ]
            },
        )
        assert resp.status_code == 200

        # Refresh user3 token to get updated claims
        user3_token = keycloak_login("test-user3", "password")["access_token"]
        pytest.user3_token = user3_token
        pytest.user3_client = make_client(user3_token)

    def test_view_project_settings_succeeds(self):
        resp = pytest.user3_client.get(
            mgmt_url(f"/projects/{pytest.project_e_id}/settings"),
        )
        assert resp.status_code == 200

    def test_update_project_settings_forbidden(self):
        resp = pytest.user3_client.patch(
            mgmt_url(f"/projects/{pytest.project_e_id}/settings"),
            json={"rate_limit": 50, "spending_limit": None, "extra": {}},
        )
        assert resp.status_code == 403

    def test_list_project_users_forbidden(self):
        resp = pytest.user3_client.get(
            mgmt_url(f"/projects/{pytest.project_e_id}/users"),
        )
        assert resp.status_code == 403

    def test_create_api_key_forbidden(self):
        resp = pytest.user3_client.post(
            mgmt_url("/api-keys"),
            params={"project_id": pytest.project_e_id},
            json={
                "name": "Forbidden Key",
                "description": "",
                "permissions": [],
            },
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 8. ORG USER & INVITE MANAGEMENT (User2)
# ---------------------------------------------------------------------------


class TestOrgUserInviteManagement:
    """Section 8: User2 gets user management permissions."""

    @pytest.fixture(autouse=True, scope="class")
    def grant_user2_management(self, user1_client: httpx.Client):
        # Grant additional permissions to User2
        resp = user1_client.put(
            org_url(f"/users/{pytest.user2_id}/permissions"),
            json={
                "permissions": [
                    "organization.projects.create",
                    "organization.projects.get_all",
                    "organization.users.get_all",
                    "organization.invite",
                ]
            },
        )
        assert resp.status_code == 200

        # Refresh user2 token
        token = keycloak_login("test-user2", "password")["access_token"]
        pytest.user2_client = make_client(token)

    def test_list_users_succeeds(self):
        resp = pytest.user2_client.get(org_url("/users"))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_invite_user4(self):
        resp = pytest.user2_client.post(
            org_url("/invitations"),
            json={"email": "test-user4@gantry.com"},
        )
        assert resp.status_code == 200

    def test_remove_user4_forbidden(self):
        # User2 lacks organization.users.remove permission
        # First we need user4's ID - sign them up
        token = signup_user_via_mailpit("test-user4@gantry.com")

        import jwt as pyjwt

        payload = pyjwt.decode(token, options={"verify_signature": False})
        user4_id = payload["sub"]
        pytest.user4_id = user4_id

        resp = pytest.user2_client.delete(
            org_url(f"/users/{user4_id}"),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 9. ORG SETTINGS & BILLING (User2 & User1)
# ---------------------------------------------------------------------------


class TestOrgSettingsBilling:
    """Section 9: Settings and billing permission tests."""

    def test_get_settings_user2_forbidden(self):
        # User2 still doesn't have settings permission
        token = keycloak_login("test-user2", "password")["access_token"]
        client = make_client(token)
        resp = client.get(org_url("/settings"))
        assert resp.status_code == 403

    def test_grant_settings_permissions(self, user1_client: httpx.Client):
        resp = user1_client.put(
            org_url(f"/users/{pytest.user2_id}/permissions"),
            json={
                "permissions": [
                    "organization.projects.create",
                    "organization.projects.get_all",
                    "organization.users.get_all",
                    "organization.invite",
                    "organization.settings.read",
                    "organization.settings.write",
                ]
            },
        )
        assert resp.status_code == 200

    def test_get_settings_user2_succeeds(self):
        token = keycloak_login("test-user2", "password")["access_token"]
        client = make_client(token)
        resp = client.get(org_url("/settings"))
        assert resp.status_code == 200

    def test_patch_settings_user2_succeeds(self):
        token = keycloak_login("test-user2", "password")["access_token"]
        client = make_client(token)
        resp = client.patch(
            org_url("/settings"),
            json={
                "rate_limit": 200,
                "spending_limit": None,
                "extra": {},
            },
        )
        assert resp.status_code == 200

    def test_get_billing_user1_succeeds(self, user1_client: httpx.Client):
        resp = user1_client.get(
            mgmt_url("/billing/aggregates/organizations"),
            params={
                "period_start": "2024-01-01T00:00:00Z",
                "period_end": "2026-12-31T00:00:00Z",
                "period": "monthly",
            },
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 10. CLEANUP (User1)
# ---------------------------------------------------------------------------


# class TestCleanup:
#     """Section 10: Remove test users and projects."""

#     def test_remove_user2(self, user1_client: httpx.Client):
#         resp = user1_client.delete(
#             org_url(f"/users/{pytest.user2_id}"),
#         )
#         assert resp.status_code == 200

#     def test_remove_user3(self, user1_client: httpx.Client):
#         resp = user1_client.delete(
#             org_url(f"/users/{pytest.user3_id}"),
#         )
#         assert resp.status_code == 200

#     def test_delete_project_d(self, user1_client: httpx.Client):
#         resp = user1_client.post(
#             mgmt_url(f"/projects/{pytest.project_d_id}/archive"),
#         )
#         assert resp.status_code == 200

#     def test_delete_project_e(self, user1_client: httpx.Client):
#         resp = user1_client.post(
#             mgmt_url(f"/projects/{pytest.project_e_id}/archive"),
#         )
#         assert resp.status_code == 200
