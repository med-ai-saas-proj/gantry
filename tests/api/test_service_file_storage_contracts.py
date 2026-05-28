from __future__ import annotations

import pytest

from uuid import UUID

from tests.api.fakes import FILE_UUID, PROJECT_UUID

pytestmark = pytest.mark.api

AUTH = {"Authorization": "Bearer user-token", "X-Api-Key": "sk_test"}


@pytest.mark.asyncio
async def test_api_key_file_storage_lifecycle_routes_delegate_project_id(service_client, authenticated_service_api) -> None:
    upload = await service_client.post(
        "/v1/file-storage/service/",
        headers=AUTH,
        files={"file": ("report.txt", b"hello", "text/plain")},
    )
    listed = await service_client.get("/v1/file-storage/service/", headers=AUTH)
    detail = await service_client.get(f"/v1/file-storage/service/{FILE_UUID}", headers=AUTH)
    info = await service_client.get(f"/v1/file-storage/service/{FILE_UUID}/info", headers=AUTH)
    url = await service_client.get(f"/v1/file-storage/service/{FILE_UUID}/presigned-url", headers=AUTH)
    download = await service_client.get(f"/v1/file-storage/service/{FILE_UUID}/download", headers=AUTH)
    deleted = await service_client.delete(f"/v1/file-storage/service/{FILE_UUID}", headers=AUTH)

    assert upload.status_code == 201
    assert upload.json()["file_id"] == FILE_UUID
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == FILE_UUID
    assert detail.json()["url"] == "https://files.example/download"
    assert info.json()["filename"] == "report.txt"
    assert url.json()["url"] == "https://files.example/download"
    assert download.status_code == 307
    assert deleted.status_code == 204
    assert ("listFilesInProject", 20) in authenticated_service_api["file_storage"].calls


@pytest.mark.asyncio
async def test_user_file_storage_routes_delegate_project_uuid_query_context(service_client, authenticated_service_api) -> None:
    listed = await service_client.get(
        "/v1/file-storage/user/",
        headers=AUTH,
        params={"project_uuid": PROJECT_UUID},
    )
    detail_without_path_context = await service_client.get(
        f"/v1/file-storage/user/{FILE_UUID}",
        headers=AUTH,
        params={"project_uuid": PROJECT_UUID},
    )
    uploaded = await service_client.post(
        "/v1/file-storage/user/",
        headers=AUTH,
        files={"file": ("report.txt", b"hello", "text/plain")},
        params={"project_uuid": PROJECT_UUID},
    )

    assert listed.status_code == 200
    assert detail_without_path_context.status_code == 400
    assert uploaded.status_code == 201
    assert ("listFilesInProjectByUUID", UUID(PROJECT_UUID)) in authenticated_service_api["file_storage"].calls


@pytest.mark.asyncio
async def test_file_upload_rejects_empty_file(service_client, authenticated_service_api) -> None:
    response = await service_client.post(
        "/v1/file-storage/service/",
        headers=AUTH,
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 400
