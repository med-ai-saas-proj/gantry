from __future__ import annotations

import pytest

from tests.api.fakes import FILE_UUID, PROJECT_UUID

pytestmark = pytest.mark.api

AUTH = {"Authorization": "Bearer user-token", "X-Api-Key": "sk_test"}


@pytest.mark.asyncio
async def test_api_key_rag_embedding_file_task_and_query_routes(service_client, authenticated_service_api) -> None:
    embedding = await service_client.post(
        "/v1/rag/service/embeddings",
        headers=AUTH,
        json={"text": "hello", "embedding": [0.1, 0.2], "file_uid": FILE_UUID},
    )
    files = await service_client.get("/v1/rag/service/files", headers=AUTH)
    add_file = await service_client.post(
        "/v1/rag/service/files",
        headers=AUTH,
        json={"file_uid": FILE_UUID, "chunk_size": 100, "chunk_overlap": 10},
    )
    task = await service_client.get("/v1/rag/service/files/task-1", headers=AUTH)
    vector = await service_client.post(
        "/v1/rag/service/query/vector",
        headers=AUTH,
        json={"embedding": [0.1, 0.2], "top_k": 3},
    )
    text = await service_client.post(
        "/v1/rag/service/query/text",
        headers=AUTH,
        json={"query_text": "hello", "top_k": 3},
    )

    assert embedding.status_code == 201
    assert files.status_code == 200
    assert files.json()[0]["id"] == FILE_UUID
    assert add_file.status_code == 201
    assert add_file.json() == "task-1"
    assert task.json()["project_uuid"] == PROJECT_UUID
    assert vector.json()[0]["file_info"]["id"] == FILE_UUID
    assert text.json()[0]["text"] == "matched text"


@pytest.mark.asyncio
async def test_user_rag_routes_currently_require_project_uuid_path_context(service_client, authenticated_service_api) -> None:
    responses = [
        await service_client.get("/v1/rag/user/files", headers=AUTH, params={"project_uuid": PROJECT_UUID}),
        await service_client.post(
            "/v1/rag/user/files",
            headers=AUTH,
            params={"project_uuid": PROJECT_UUID},
            json={"file_uid": FILE_UUID, "chunk_size": 100, "chunk_overlap": 10},
        ),
        await service_client.get("/v1/rag/user/files/task-1", headers=AUTH, params={"project_uuid": PROJECT_UUID}),
    ]

    assert {response.status_code for response in responses} == {400}


@pytest.mark.asyncio
async def test_rag_query_rejects_invalid_top_k(service_client, authenticated_service_api) -> None:
    response = await service_client.post(
        "/v1/rag/service/query/text",
        headers=AUTH,
        json={"query_text": "hello", "top_k": 0},
    )

    assert response.status_code in {400, 422}
