from __future__ import annotations

import os

from locust import HttpUser, between, task


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _api_key_headers(api_key: str) -> dict[str, str]:
    return {"X-Api-Key": api_key} if api_key else {}


def _assert_no_5xx(response, name: str) -> None:
    if response.status_code >= 500:
        response.failure(f"{name} returned {response.status_code}")
    else:
        response.success()


class PublicCatalogUser(HttpUser):
    wait_time = between(1, 3)
    weight = 4

    @task(5)
    def permission_catalogs(self) -> None:
        for path in [
            "/management/v1/organizations/permissions",
            "/management/v1/projects/permissions",
            "/management/v1/api-keys/permissions",
        ]:
            with self.client.get(path, catch_response=True, name=path) as response:
                _assert_no_5xx(response, path)


class ManagementUser(HttpUser):
    wait_time = between(1, 2)
    weight = 3

    def on_start(self) -> None:
        self.headers = _auth_headers(os.getenv("LOCUST_USER_TOKEN", ""))
        self.project_uuid = os.getenv("LOCUST_PROJECT_UUID", "")
        self.api_key_uuid = os.getenv("LOCUST_API_KEY_UUID", "")

    @task(3)
    def browse_projects(self) -> None:
        with self.client.get(
            "/management/v1/projects",
            headers=self.headers,
            catch_response=True,
            name="GET /management/v1/projects",
        ) as response:
            _assert_no_5xx(response, "projects")

    @task(2)
    def browse_project_api_keys(self) -> None:
        params = {"project_id": self.project_uuid} if self.project_uuid else {}
        with self.client.get(
            "/management/v1/api-keys",
            params=params,
            headers=self.headers,
            catch_response=True,
            name="GET /management/v1/api-keys",
        ) as response:
            _assert_no_5xx(response, "api keys")

    @task(1)
    def read_api_key(self) -> None:
        if not self.api_key_uuid:
            return
        path = f"/management/v1/api-keys/{self.api_key_uuid}"
        with self.client.get(
            path,
            headers=self.headers,
            catch_response=True,
            name="GET /management/v1/api-keys/{api_key_uuid}",
        ) as response:
            _assert_no_5xx(response, "api key detail")


class AdminDashboardUser(HttpUser):
    wait_time = between(1, 2)
    weight = 2

    def on_start(self) -> None:
        self.headers = _auth_headers(os.getenv("LOCUST_ADMIN_TOKEN", ""))

    @task(3)
    def dashboard_summary(self) -> None:
        with self.client.get(
            "/management/v1/admin/dashboard/summary",
            headers=self.headers,
            catch_response=True,
            name="GET /management/v1/admin/dashboard/summary",
        ) as response:
            _assert_no_5xx(response, "admin summary")

    @task(1)
    def list_users(self) -> None:
        with self.client.get(
            "/management/v1/admin/users",
            headers=self.headers,
            catch_response=True,
            name="GET /management/v1/admin/users",
        ) as response:
            _assert_no_5xx(response, "admin users")


class ApiKeyServiceUser(HttpUser):
    wait_time = between(1, 2)
    weight = 1

    def on_start(self) -> None:
        self.headers = _api_key_headers(os.getenv("LOCUST_API_KEY", ""))
        self.file_id = os.getenv("LOCUST_FILE_ID", "")
        self.conversation_uid = os.getenv("LOCUST_CONVERSATION_UID", "")

    @task(2)
    def list_service_files(self) -> None:
        with self.client.get(
            "/service/v1/file-storage/service/",
            headers=self.headers,
            catch_response=True,
            name="GET /service/v1/file-storage/service/",
        ) as response:
            _assert_no_5xx(response, "service files")

    @task(1)
    def read_conversation(self) -> None:
        if not self.conversation_uid:
            return
        with self.client.get(
            f"/service/v1/conversations/{self.conversation_uid}",
            headers=self.headers,
            catch_response=True,
            name="GET /service/v1/conversations/{conversation_uid}",
        ) as response:
            _assert_no_5xx(response, "conversation")
