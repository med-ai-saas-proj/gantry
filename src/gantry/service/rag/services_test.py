import os
import json
import unittest
from uuid import UUID, uuid4
from types import SimpleNamespace
from typing import Sequence, cast
from unittest.mock import ANY, Mock, AsyncMock, MagicMock, patch


os.environ.setdefault("GANTRY_SERVER__CONFIG_FILE", "gantry.toml")

from gantry.db.session import AsyncSessionManager
from gantry.settings.rag import VectorOpsType, VectorIndexType
from gantry.service.rag.type import EmbeddingTask, ChunkSplitterType
from gantry.service.rag.models import RagMetadata
from gantry.service.rag.services import (
    RagService,
    TaskNotFoundError,
    BucketNotFoundError,
    FileNotFoundInSystemError,
    InvalidEmbeddingDimensionError,
)
from gantry.service.rag.settings import RagSettings

from pyrusult import Ok, Err, ResultStatus


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _SessionManager:
    def __init__(self, session):
        self._session = session

    def get_session(self):
        return _SessionContext(self._session)


def _make_rag_settings():
    settings = Mock(spec=RagSettings)
    settings.embedding_model = "text-embedding-3-small"
    settings.rag_store_parameters = {
        "dimension": 1536,
        "index_params": {
            "index_type": VectorIndexType.hnsw,
            "m": 16,
            "ef_construction": 200,
        },
        "ops_type": VectorOpsType.cosine,
    }
    return settings


def _make_service(
    *,
    session=None,
    project_repo=None,
    file_repo=None,
    openai_client=None,
    redis=None,
    logger=None,
):
    session = session or Mock()
    session.execute = AsyncMock()
    session.add = Mock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.expunge_all = Mock()

    project_repo = project_repo or Mock()
    file_repo = file_repo or Mock()

    openai_client = openai_client or Mock()

    if redis is None:
        redis = Mock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        redis.delete = AsyncMock()
        redis.blpop = AsyncMock(return_value=None)
        redis.rpush = AsyncMock()
        redis.pipeline = MagicMock()
        redis.pipeline.return_value.__aenter__ = AsyncMock()
        redis.pipeline.return_value.__aexit__ = AsyncMock()

    logger = logger or Mock()

    settings = _make_rag_settings()

    return (
        RagService(
            session_manager=cast(AsyncSessionManager, _SessionManager(session)),
            project_repo=project_repo,
            file_repo=file_repo,
            setting=settings,
            file_storage_service=Mock(),
            openai_client=openai_client,
            redis=redis,
            logger=logger,
        ),
        session,
        project_repo,
        file_repo,
        openai_client,
        redis,
        logger,
    )


class TestRagService(unittest.IsolatedAsyncioTestCase):
    async def test_create_bucket_creates_table_and_index(self):
        service, session, _, _, _, _, _ = _make_service()

        with (
            patch(
                "gantry.service.rag.services.create_embedding_table",
                new=AsyncMock(),
            ) as mock_create_table,
            patch(
                "gantry.service.rag.services.create_vector_index",
                new=AsyncMock(),
            ) as mock_create_index,
        ):
            await service.createBucket()

            mock_create_table.assert_awaited_once()
            mock_create_index.assert_awaited_once()
            session.commit.assert_awaited_once()

    async def test_add_file_returns_task_id_when_file_exists(self):
        file_uid = uuid4()
        project_id = 17
        project_uuid = uuid4()

        service, session, _, file_repo, _, redis, _ = _make_service()

        file_repo.getAvailableByUUID = AsyncMock(
            return_value=SimpleNamespace(id=5, uuid=file_uid)
        )

        pipe_mock = AsyncMock()
        pipe_mock.__aenter__ = AsyncMock(return_value=pipe_mock)
        pipe_mock.__aexit__ = AsyncMock(return_value=False)
        pipe_mock.set = AsyncMock()
        pipe_mock.rpush = AsyncMock()
        pipe_mock.execute = AsyncMock()
        redis.pipeline.return_value = pipe_mock

        result = await service.addFile(
            file_uid=file_uid,
            project_id=project_id,
            project_uuid=project_uuid,
            chunk_splitter=ChunkSplitterType.recursive,
            chunk_size=1000,
            chunk_overlap=150,
        )

        assert result.status == ResultStatus.Ok
        task_id = result.unwrap()
        assert isinstance(task_id, str)
        file_repo.getAvailableByUUID.assert_awaited_once_with(
            session, file_uid, project_id
        )
        pipe_mock.set.assert_called_once()
        pipe_mock.rpush.assert_called_once()

    async def test_add_file_returns_error_when_file_not_found(self):
        file_uid = uuid4()
        project_id = 17
        project_uuid = uuid4()

        service, session, _, file_repo, _, _, _ = _make_service()

        file_repo.getAvailableByUUID = AsyncMock(return_value=None)

        result = await service.addFile(
            file_uid=file_uid,
            project_id=project_id,
            project_uuid=project_uuid,
        )

        assert result.status == ResultStatus.Err
        error = result.err()
        assert isinstance(error, FileNotFoundInSystemError)

    async def test_get_task_status_returns_task_when_found(self):
        task_id = str(uuid4())
        project_id = 17
        file_uid = uuid4()
        project_uuid = uuid4()

        service, _, _, _, _, redis, _ = _make_service()

        task_dict = {
            "task_id": task_id,
            "file_id": 5,
            "file_uid": str(file_uid),
            "project_id": project_id,
            "project_uuid": str(project_uuid),
            "chunk_splitter": "recursive",
            "chunk_size": 1000,
            "chunk_overlap": 150,
            "status": "pending",
            "failed_reason": None,
        }
        redis.get = AsyncMock(return_value=json.dumps(task_dict))

        result = await service.getTaskStatus(task_id, project_id)

        assert result.status == ResultStatus.Ok
        task = result.unwrap()
        assert task["task_id"] == task_id
        assert task["project_id"] == project_id
        assert task["status"] == "pending"

    async def test_get_task_status_returns_error_when_not_found(self):
        task_id = str(uuid4())
        project_id = 17

        service, _, _, _, _, redis, _ = _make_service()

        redis.get = AsyncMock(return_value=None)

        result = await service.getTaskStatus(task_id, project_id)

        assert result.status == ResultStatus.Err
        assert isinstance(result.err(), TaskNotFoundError)

    async def test_get_task_status_returns_error_when_project_mismatch(self):
        task_id = str(uuid4())
        project_id = 17
        file_uid = uuid4()
        project_uuid = uuid4()

        service, _, _, _, _, redis, _ = _make_service()

        task_dict = {
            "task_id": task_id,
            "file_id": 5,
            "file_uid": str(file_uid),
            "project_id": 99,
            "project_uuid": str(project_uuid),
            "chunk_splitter": "recursive",
            "chunk_size": 1000,
            "chunk_overlap": 150,
            "status": "pending",
        }
        redis.get = AsyncMock(return_value=json.dumps(task_dict))

        result = await service.getTaskStatus(task_id, project_id)

        assert result.status == ResultStatus.Err
        assert isinstance(result.err(), TaskNotFoundError)

    async def test_add_embedding_stores_when_valid(self):
        file_uid = uuid4()
        project_id = 17
        embedding = [0.1] * 1536

        service, session, _, file_repo, _, _, _ = _make_service()

        file_repo.getAvailableByUUID = AsyncMock(
            return_value=SimpleNamespace(id=5, uuid=file_uid)
        )

        with patch(
            "gantry.service.rag.services.get_orm_class",
            return_value=Mock,
        ):
            result = await service.addEmbedding(
                text="sample text",
                embedding=embedding,
                file_uid=file_uid,
                project_id=project_id,
            )

        assert result.status == ResultStatus.Ok
        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_add_embedding_returns_error_on_dimension_mismatch(self):
        file_uid = uuid4()
        project_id = 17
        embedding = [0.1] * 512  # Wrong dimension

        service, _, _, _, _, _, _ = _make_service()

        result = await service.addEmbedding(
            text="sample text",
            embedding=embedding,
            file_uid=file_uid,
            project_id=project_id,
        )

        assert result.status == ResultStatus.Err
        error = result.err()
        assert isinstance(error, InvalidEmbeddingDimensionError)

    async def test_add_embedding_returns_error_when_file_not_found(self):
        file_uid = uuid4()
        project_id = 17
        embedding = [0.1] * 1536

        service, session, _, file_repo, _, _, _ = _make_service()

        file_repo.getAvailableByUUID = AsyncMock(return_value=None)

        result = await service.addEmbedding(
            text="sample text",
            embedding=embedding,
            file_uid=file_uid,
            project_id=project_id,
        )

        assert result.status == ResultStatus.Err
        assert isinstance(result.err(), FileNotFoundInSystemError)

    async def test_get_files_in_rag_returns_file_records(self):
        project_id = 17

        service, session, _, file_repo, _, _, _ = _make_service()

        execute_res = Mock()
        execute_res.scalars.return_value.all.return_value = [5, 6]
        session.execute = AsyncMock(return_value=execute_res)

        file_uid_1 = uuid4()
        file_uid_2 = uuid4()
        file_repo.getAvailableByIds = AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=5,
                    uuid=file_uid_1,
                    original_filename="doc1.pdf",
                    mime_type="application/pdf",
                    size_in_bytes=1024,
                    created_at="2026-01-01T00:00:00Z",
                    extra_metadata={},
                    filepath="/uploads/doc1.pdf",
                ),
                SimpleNamespace(
                    id=6,
                    uuid=file_uid_2,
                    original_filename="doc2.pdf",
                    mime_type="application/pdf",
                    size_in_bytes=2048,
                    created_at="2026-01-02T00:00:00Z",
                    extra_metadata={},
                    filepath="/uploads/doc2.pdf",
                ),
            ]
        )

        result = await service.getFilesInRag(project_id)

        assert len(result) == 2
        assert result[0]["filename"] == "doc1.pdf"
        assert result[1]["filename"] == "doc2.pdf"
        file_repo.getAvailableByIds.assert_awaited_once_with(session, [5, 6])

    async def test_get_files_in_rag_returns_empty_when_no_files(self):
        project_id = 17

        service, session, _, file_repo, _, _, _ = _make_service()

        execute_res = Mock()
        execute_res.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=execute_res)

        file_repo.getAvailableByIds = AsyncMock(return_value=[])

        result = await service.getFilesInRag(project_id)

        assert len(result) == 0

    async def test_query_similar_by_vector_returns_error_on_dimension_mismatch(
        self,
    ):
        project_id = 17
        embedding = [0.1] * 512  # Wrong dimension

        service, _, _, _, _, _, _ = _make_service()

        result = await service.querySimilarByVector(
            project_id=project_id,
            embedding=embedding,
            top_k=5,
        )

        assert result.status == ResultStatus.Err
        error = result.err()
        assert isinstance(error, InvalidEmbeddingDimensionError)

    async def test_split_by_character_window_creates_chunks(self):
        service, _, _, _, _, _, _ = _make_service()

        text = "a" * 1000
        chunks = service._splitByCharacterWindow(
            text_content=text,
            chunk_size=100,
            chunk_overlap=10,
        )

        assert len(chunks) > 0
        assert all(len(chunk) <= 100 for chunk in chunks)

    async def test_split_by_token_window_creates_chunks(self):
        service, _, _, _, _, _, _ = _make_service()

        text = " ".join(["word"] * 100)
        chunks = service._splitByTokenWindow(
            text_content=text,
            chunk_size=10,
            chunk_overlap=2,
        )

        assert len(chunks) > 0

    async def test_split_by_markdown_sections_handles_headers(self):
        service, _, _, _, _, _, _ = _make_service()

        text = "# Header 1\nContent 1\n## Header 2\nContent 2"
        chunks = service._splitByMarkdownSections(
            text_content=text,
            chunk_size=1000,
            chunk_overlap=0,
        )

        assert len(chunks) > 0
