import os
import json
import unittest
from uuid import UUID, uuid4
from types import SimpleNamespace
from typing import Sequence, cast
from contextlib import ExitStack
from unittest.mock import ANY, Mock, AsyncMock, MagicMock, patch


os.environ.setdefault("GANTRY_SERVER__CONFIG_FILE", "gantry.toml")

from gantry.db.session import AsyncSessionManager
from gantry.settings.rag import VectorOpsType, VectorIndexType
from gantry.service.rag.dtos import (
    AddRagFileRequest,
    AddTextToRagRequest,
    EmbeddingTaskResponse,
)
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
from langchain_text_splitters import Language


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
    settings.supported_langs_list = ["simple"]
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
            reranker=Mock(),
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
            patch(
                "gantry.service.rag.services.create_bm25_index",
                new=AsyncMock(),
            ) as mock_create_bm25_index,
        ):
            await service.createBucket()

            mock_create_table.assert_awaited_once()
            mock_create_index.assert_awaited_once()
            mock_create_bm25_index.assert_awaited_once()
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
            chunk_splitter_options={"separators": ["\n\n"]},
        )

        assert result.status == ResultStatus.Ok
        task_id = result.unwrap()
        assert isinstance(task_id, str)
        file_repo.getAvailableByUUID.assert_awaited_once_with(
            session, file_uid, project_id
        )
        pipe_mock.set.assert_called_once()
        pipe_mock.rpush.assert_called_once()
        payload = json.loads(pipe_mock.set.call_args.args[1])
        assert payload["chunk_splitter"] == "recursive"
        assert payload["chunk_splitter_options"] == {"separators": ["\n\n"]}

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
            "chunk_splitter_options": {"separators": ["\n\n"]},
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
        assert task["chunk_splitter_options"] == {"separators": ["\n\n"]}

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

    async def test_split_by_code_language_cpp_uses_recursive_language(self):
        service, _, _, _, _, _, _ = _make_service()

        text = "int main() { return 0; }"
        chunks = service._splitWithLangChainSplitter(
            text_content=text,
            chunk_splitter=ChunkSplitterType.code_language_cpp,
            chunk_size=1000,
            chunk_overlap=0,
        )

        assert len(chunks) == 1
        assert "int main" in chunks[0]

    async def test_split_recursive_json_parses_json_text(self):
        service, _, _, _, _, _, _ = _make_service()

        text = '{"a": {"b": 1}, "c": [1, 2, 3]}'
        chunks = service._splitWithLangChainSplitter(
            text_content=text,
            chunk_splitter=ChunkSplitterType.recursive_json,
            chunk_size=1000,
            chunk_overlap=0,
            chunk_splitter_options={},
        )

        assert len(chunks) == 1
        assert chunks[0].startswith("{")

    async def test_split_code_language_python_and_jsx(self):
        service, _, _, _, _, _, _ = _make_service()

        python_chunks = service._splitWithLangChainSplitter(
            text_content="def hello():\n    return 1",
            chunk_splitter=ChunkSplitterType.code_language_python,
            chunk_size=1000,
            chunk_overlap=0,
        )
        jsx_chunks = service._splitWithLangChainSplitter(
            text_content="export function Button() { return <div>Hello</div>; }",
            chunk_splitter=ChunkSplitterType.code_language_jsx,
            chunk_size=1000,
            chunk_overlap=0,
        )

        assert len(python_chunks) == 1
        assert "def hello" in python_chunks[0]
        assert len(jsx_chunks) == 1
        assert "Button" in jsx_chunks[0]

    async def test_splitter_option_schema_exposes_all_splitter_defs(self):
        expected_defs = {
            "CharacterTextSplitterOptions",
            "RecursiveCharacterTextSplitterOptions",
            "TokenTextSplitterOptions",
            "MarkdownHeaderTextSplitterOptions",
            "MarkdownTextSplitterOptions",
            "ExperimentalMarkdownSyntaxTextSplitterOptions",
            "HTMLHeaderTextSplitterOptions",
            "HTMLSemanticPreservingSplitterOptions",
            "HTMLSectionSplitterOptions",
            "RecursiveJsonSplitterOptions",
            "NLTKTextSplitterOptions",
            "SpacyTextSplitterOptions",
            "KonlpyTextSplitterOptions",
            "SentenceTransformersTokenTextSplitterOptions",
            "RecursiveCharacterLanguageTextSplitterOptions",
        }

        for dto_class in (
            AddTextToRagRequest,
            AddRagFileRequest,
            EmbeddingTaskResponse,
        ):
            with self.subTest(dto=dto_class.__name__):
                schema = dto_class.model_json_schema()
                splitter_schema = schema["properties"]["chunk_splitter_options"]
                self.assertIn("anyOf", splitter_schema)
                self.assertTrue(
                    expected_defs.issubset(set(schema.get("$defs", {}).keys()))
                )

    async def test_splitter_dispatches_non_code_splitters(self):
        service, _, _, _, _, _, _ = _make_service()

        cases = [
            {
                "name": "simple",
                "splitter": ChunkSplitterType.simple,
                "text": "a" * 30,
                "constructor": "gantry.service.rag.services.CharacterTextSplitter",
                "mock_method": "split_text",
                "mock_result": ["simple chunk"],
                "expected_result": ["simple chunk"],
                "expected_kwargs": {
                    "separator": "\n",
                    "chunk_size": 1000,
                    "chunk_overlap": 0,
                },
                "options": {"separator": "\n"},
            },
            {
                "name": "character",
                "splitter": ChunkSplitterType.character,
                "text": "b" * 30,
                "constructor": "gantry.service.rag.services.CharacterTextSplitter",
                "mock_method": "split_text",
                "mock_result": ["character chunk"],
                "expected_result": ["character chunk"],
                "expected_kwargs": {"chunk_size": 25, "chunk_overlap": 5},
                "options": {"chunk_size": 25, "chunk_overlap": 5},
            },
            {
                "name": "recursive",
                "splitter": ChunkSplitterType.recursive,
                "text": "one two three four",
                "constructor": "gantry.service.rag.services.RecursiveCharacterTextSplitter",
                "mock_method": "split_text",
                "mock_result": ["recursive chunk"],
                "expected_result": ["recursive chunk"],
                "expected_kwargs": {
                    "separators": ["\n\n"],
                    "chunk_size": 1000,
                    "chunk_overlap": 0,
                },
                "options": {"separators": ["\n\n"]},
            },
            {
                "name": "token",
                "splitter": ChunkSplitterType.token,
                "text": "one two three four",
                "constructor": "gantry.service.rag.services.TokenTextSplitter",
                "mock_method": "split_text",
                "mock_result": ["token chunk"],
                "expected_result": ["token chunk"],
                "expected_kwargs": {
                    "chunk_size": 1000,
                    "chunk_overlap": 0,
                    "encoding_name": "cl100k_base",
                },
                "options": {"encoding_name": "cl100k_base"},
            },
            {
                "name": "markdown",
                "splitter": ChunkSplitterType.markdown,
                "text": "# Title\ncontent",
                "constructor": "gantry.service.rag.services.MarkdownTextSplitter",
                "mock_method": "split_text",
                "mock_result": ["markdown chunk"],
                "expected_result": ["markdown chunk"],
                "expected_kwargs": {"chunk_size": 1000, "chunk_overlap": 0},
                "options": {},
            },
            {
                "name": "markdown_header",
                "splitter": ChunkSplitterType.markdown_header,
                "text": "# Title\ncontent",
                "constructor": "gantry.service.rag.services.MarkdownHeaderTextSplitter",
                "mock_method": "split_text",
                "mock_result": ["markdown header chunk"],
                "expected_result": ["markdown header chunk"],
                "expected_kwargs": {
                    "headers_to_split_on": [
                        ("#", "Header 1"),
                        ("##", "Header 2"),
                        ("###", "Header 3"),
                        ("####", "Header 4"),
                        ("#####", "Header 5"),
                        ("######", "Header 6"),
                    ]
                },
                "options": {},
            },
            {
                "name": "html",
                "splitter": ChunkSplitterType.html,
                "text": "<html><body><h1>Title</h1><p>Body</p></body></html>",
                "constructor": "gantry.service.rag.services.HTMLHeaderTextSplitter",
                "mock_method": "split_text",
                "mock_result": ["html chunk"],
                "expected_result": ["html chunk"],
                "expected_kwargs": {
                    "headers_to_split_on": [
                        ("h1", "Header 1"),
                        ("h2", "Header 2"),
                        ("h3", "Header 3"),
                        ("h4", "Header 4"),
                        ("h5", "Header 5"),
                        ("h6", "Header 6"),
                    ]
                },
                "options": {},
            },
            {
                "name": "html_header",
                "splitter": ChunkSplitterType.html_header,
                "text": "<html><body><h1>Title</h1><p>Body</p></body></html>",
                "constructor": "gantry.service.rag.services.HTMLHeaderTextSplitter",
                "mock_method": "split_text",
                "mock_result": ["html header chunk"],
                "expected_result": ["html header chunk"],
                "expected_kwargs": {
                    "headers_to_split_on": [
                        ("h1", "Header 1"),
                        ("h2", "Header 2"),
                        ("h3", "Header 3"),
                        ("h4", "Header 4"),
                        ("h5", "Header 5"),
                        ("h6", "Header 6"),
                    ]
                },
                "options": {},
            },
            {
                "name": "html_semantic_preserving",
                "splitter": ChunkSplitterType.html_semantic_preserving,
                "text": "<html><body><h1>Title</h1><p>Body</p></body></html>",
                "constructor": "gantry.service.rag.services.HTMLSemanticPreservingSplitter",
                "mock_method": "split_text",
                "mock_result": ["html semantic chunk"],
                "expected_result": ["html semantic chunk"],
                "expected_kwargs": {
                    "headers_to_split_on": [
                        ("h1", "Header 1"),
                        ("h2", "Header 2"),
                        ("h3", "Header 3"),
                        ("h4", "Header 4"),
                        ("h5", "Header 5"),
                        ("h6", "Header 6"),
                    ],
                    "max_chunk_size": 1000,
                    "chunk_overlap": 0,
                    "preserve_links": True,
                },
                "options": {"preserve_links": True},
            },
            {
                "name": "html_section",
                "splitter": ChunkSplitterType.html_section,
                "text": "<html><body><h1>Title</h1><p>Body</p></body></html>",
                "constructor": "gantry.service.rag.services.HTMLSectionSplitter",
                "mock_method": "split_text",
                "mock_result": ["html section chunk"],
                "expected_result": ["html section chunk"],
                "expected_kwargs": {
                    "headers_to_split_on": [
                        ("h1", "Header 1"),
                        ("h2", "Header 2"),
                        ("h3", "Header 3"),
                        ("h4", "Header 4"),
                        ("h5", "Header 5"),
                        ("h6", "Header 6"),
                    ]
                },
                "options": {},
            },
            {
                "name": "recursive_json",
                "splitter": ChunkSplitterType.recursive_json,
                "text": '{"a": {"b": 1}, "c": [1, 2, 3]}',
                "constructor": "gantry.service.rag.services.RecursiveJsonSplitter",
                "mock_method": "split_json",
                "mock_result": [{"chunk": "json"}],
                "expected_result": ['{"chunk": "json"}'],
                "expected_kwargs": {"max_chunk_size": 1000},
                "options": {"convert_lists": True},
            },
            {
                "name": "experimental_markdown_syntax",
                "splitter": ChunkSplitterType.experimental_markdown_syntax,
                "text": "# Title\nbody",
                "constructor": "gantry.service.rag.services.ExperimentalMarkdownSyntaxTextSplitter",
                "mock_method": "split_text",
                "mock_result": ["experimental markdown chunk"],
                "expected_result": ["experimental markdown chunk"],
                "expected_kwargs": {},
                "options": {"return_each_line": True},
            },
            {
                "name": "nltk",
                "splitter": ChunkSplitterType.nltk,
                "text": "Sentence one. Sentence two.",
                "constructor": "gantry.service.rag.services.NLTKTextSplitter",
                "mock_method": "split_text",
                "mock_result": ["nltk chunk"],
                "expected_result": ["nltk chunk"],
                "expected_kwargs": {
                    "chunk_size": 1000,
                    "chunk_overlap": 0,
                    "language": "english",
                },
                "options": {"language": "english"},
            },
            {
                "name": "spacy",
                "splitter": ChunkSplitterType.spacy,
                "text": "Sentence one. Sentence two.",
                "constructor": "gantry.service.rag.services.SpacyTextSplitter",
                "mock_method": "split_text",
                "mock_result": ["spacy chunk"],
                "expected_result": ["spacy chunk"],
                "expected_kwargs": {
                    "chunk_size": 1000,
                    "chunk_overlap": 0,
                    "pipeline": "en_core_web_sm",
                },
                "options": {"pipeline": "en_core_web_sm"},
            },
            {
                "name": "konlpy",
                "splitter": ChunkSplitterType.konlpy,
                "text": "한국어 문장입니다.",
                "constructor": "gantry.service.rag.services.KonlpyTextSplitter",
                "mock_method": "split_text",
                "mock_result": ["konlpy chunk"],
                "expected_result": ["konlpy chunk"],
                "expected_kwargs": {"chunk_size": 1000, "chunk_overlap": 0},
                "options": {},
            },
            {
                "name": "sentence_transformers_token",
                "splitter": ChunkSplitterType.sentence_transformers_token,
                "text": "Token splitter text",
                "constructor": "gantry.service.rag.services.SentenceTransformersTokenTextSplitter",
                "mock_method": "split_text",
                "mock_result": ["sentence transformer chunk"],
                "expected_result": ["sentence transformer chunk"],
                "expected_kwargs": {
                    "chunk_size": 1000,
                    "chunk_overlap": 0,
                    "model_name": "sentence-transformers/all-mpnet-base-v2",
                },
                "options": {
                    "model_name": "sentence-transformers/all-mpnet-base-v2"
                },
            },
            {
                "name": "paragraph",
                "splitter": ChunkSplitterType.paragraph,
                "text": "para one\n\npara two",
                "constructor": "gantry.service.rag.services.CharacterTextSplitter",
                "mock_method": "split_text",
                "mock_result": ["paragraph chunk"],
                "expected_result": ["paragraph chunk"],
                "expected_kwargs": {
                    "separator": "\n\n",
                    "chunk_size": 1000,
                    "chunk_overlap": 0,
                },
                "options": {},
            },
            {
                "name": "line",
                "splitter": ChunkSplitterType.line,
                "text": "line one\nline two",
                "constructor": "gantry.service.rag.services.CharacterTextSplitter",
                "mock_method": "split_text",
                "mock_result": ["line chunk"],
                "expected_result": ["line chunk"],
                "expected_kwargs": {
                    "separator": "\n",
                    "chunk_size": 1000,
                    "chunk_overlap": 0,
                },
                "options": {},
            },
        ]

        for case in cases:
            with self.subTest(splitter=case["name"]):
                mock_splitter = Mock()
                getattr(mock_splitter, case["mock_method"]).return_value = case[
                    "mock_result"
                ]

                with ExitStack() as stack:
                    constructor_mock = stack.enter_context(
                        patch(case["constructor"], return_value=mock_splitter)
                    )
                    chunks = service._splitWithLangChainSplitter(
                        text_content=case["text"],
                        chunk_splitter=case["splitter"],
                        chunk_size=1000,
                        chunk_overlap=0,
                        chunk_splitter_options=case["options"],
                    )

                constructor_mock.assert_called_once()
                if case["name"] == "recursive_json":
                    mock_splitter.split_json.assert_called_once_with(
                        {"a": {"b": 1}, "c": [1, 2, 3]},
                        convert_lists=True,
                    )
                else:
                    mock_splitter.split_text.assert_called_once()

                self.assertEqual(chunks, case["expected_result"])
                for key, value in case["expected_kwargs"].items():
                    self.assertEqual(
                        constructor_mock.call_args.kwargs[key], value
                    )

    async def test_splitter_dispatches_code_language_splitters(self):
        service, _, _, _, _, _, _ = _make_service()

        cases = [
            {
                "name": "python",
                "splitter": ChunkSplitterType.code_language_python,
                "text": "def hello():\n    return 1",
                "constructor": "gantry.service.rag.services.PythonCodeTextSplitter",
                "mock_result": ["python chunk"],
                "expected_result": ["python chunk"],
                "expected_kwargs": {
                    "chunk_size": 200,
                    "chunk_overlap": 10,
                },
                "options": {"chunk_size": 200, "chunk_overlap": 10},
                "from_language": None,
            },
            {
                "name": "jsx",
                "splitter": ChunkSplitterType.code_language_jsx,
                "text": "export function Button() { return <div />; }",
                "constructor": "gantry.service.rag.services.JSFrameworkTextSplitter",
                "mock_result": ["jsx chunk"],
                "expected_result": ["jsx chunk"],
                "expected_kwargs": {
                    "chunk_size": 200,
                    "chunk_overlap": 10,
                },
                "options": {"chunk_size": 200, "chunk_overlap": 10},
                "from_language": None,
            },
            {
                "name": "c",
                "splitter": ChunkSplitterType.code_language_c,
                "text": "int main(void) { return 0; }",
                "language": Language.C,
            },
            {
                "name": "cobol",
                "splitter": ChunkSplitterType.code_language_cobol,
                "text": "IDENTIFICATION DIVISION.",
                "language": Language.COBOL,
            },
            {
                "name": "cpp",
                "splitter": ChunkSplitterType.code_language_cpp,
                "text": "int main() { return 0; }",
                "language": Language.CPP,
            },
            {
                "name": "csharp",
                "splitter": ChunkSplitterType.code_language_csharp,
                "text": "class Program { static void Main() {} }",
                "language": Language.CSHARP,
            },
            {
                "name": "go",
                "splitter": ChunkSplitterType.code_language_go,
                "text": "package main",
                "language": Language.GO,
            },
            {
                "name": "haskell",
                "splitter": ChunkSplitterType.code_language_haskell,
                "text": 'main = putStrLn "hi"',
                "language": Language.HASKELL,
            },
            {
                "name": "html_code",
                "splitter": ChunkSplitterType.code_language_html,
                "text": "<html><body></body></html>",
                "language": Language.HTML,
            },
            {
                "name": "java",
                "splitter": ChunkSplitterType.code_language_java,
                "text": "class A {}",
                "language": Language.JAVA,
            },
            {
                "name": "kotlin",
                "splitter": ChunkSplitterType.code_language_kotlin,
                "text": "fun main() {}",
                "language": Language.KOTLIN,
            },
            {
                "name": "latex_code",
                "splitter": ChunkSplitterType.code_language_latex,
                "text": "\\begin{document}",
                "language": Language.LATEX,
            },
            {
                "name": "lua",
                "splitter": ChunkSplitterType.code_language_lua,
                "text": "print('hi')",
                "language": Language.LUA,
            },
            {
                "name": "markdown_code",
                "splitter": ChunkSplitterType.code_language_markdown,
                "text": "# Title",
                "language": Language.MARKDOWN,
            },
            {
                "name": "perl",
                "splitter": ChunkSplitterType.code_language_perl,
                "text": 'print "hi";',
                "language": Language.PERL,
            },
            {
                "name": "php",
                "splitter": ChunkSplitterType.code_language_php,
                "text": "<?php echo 'hi';",
                "language": Language.PHP,
            },
            {
                "name": "proto",
                "splitter": ChunkSplitterType.code_language_proto,
                "text": "message A {}",
                "language": Language.PROTO,
            },
            {
                "name": "rst",
                "splitter": ChunkSplitterType.code_language_rst,
                "text": "Heading\n=======",
                "language": Language.RST,
            },
            {
                "name": "ruby",
                "splitter": ChunkSplitterType.code_language_ruby,
                "text": "puts 'hi'",
                "language": Language.RUBY,
            },
            {
                "name": "rust",
                "splitter": ChunkSplitterType.code_language_rust,
                "text": "fn main() {}",
                "language": Language.RUST,
            },
            {
                "name": "scala",
                "splitter": ChunkSplitterType.code_language_scala,
                "text": "object Main {}",
                "language": Language.SCALA,
            },
            {
                "name": "sol",
                "splitter": ChunkSplitterType.code_language_sol,
                "text": "contract A {}",
                "language": Language.SOL,
            },
            {
                "name": "swift",
                "splitter": ChunkSplitterType.code_language_swift,
                "text": "struct A {}",
                "language": Language.SWIFT,
            },
            {
                "name": "ts",
                "splitter": ChunkSplitterType.code_language_ts,
                "text": "const a: number = 1;",
                "language": Language.TS,
            },
        ]

        for case in cases:
            with self.subTest(splitter=case["name"]):
                if case["name"] in {"python", "jsx"}:
                    mock_splitter = Mock()
                    mock_splitter.split_text.return_value = case["mock_result"]
                    with ExitStack() as stack:
                        constructor_mock = stack.enter_context(
                            patch(
                                case["constructor"], return_value=mock_splitter
                            )
                        )
                        chunks = service._splitWithLangChainSplitter(
                            text_content=case["text"],
                            chunk_splitter=case["splitter"],
                            chunk_size=1000,
                            chunk_overlap=0,
                            chunk_splitter_options=case["options"],
                        )

                    constructor_mock.assert_called_once()
                    self.assertEqual(chunks, case["expected_result"])
                    for key, value in case["expected_kwargs"].items():
                        self.assertEqual(
                            constructor_mock.call_args.kwargs[key], value
                        )
                    continue

                mock_splitter = Mock()
                mock_splitter.split_text.return_value = [
                    f"{case['name']} chunk"
                ]

                with ExitStack() as stack:
                    from_language_mock = stack.enter_context(
                        patch(
                            "gantry.service.rag.services.RecursiveCharacterTextSplitter.from_language",
                            return_value=mock_splitter,
                        )
                    )
                    chunks = service._splitWithLangChainSplitter(
                        text_content=case["text"],
                        chunk_splitter=case["splitter"],
                        chunk_size=1000,
                        chunk_overlap=0,
                        chunk_splitter_options={"separators": ["\n\n"]},
                    )

                from_language_mock.assert_called_once()
                self.assertEqual(
                    from_language_mock.call_args.args[0], case["language"]
                )
                self.assertEqual(chunks, [f"{case['name']} chunk"])
                self.assertEqual(
                    from_language_mock.call_args.kwargs["chunk_size"], 1000
                )
                self.assertEqual(
                    from_language_mock.call_args.kwargs["chunk_overlap"], 0
                )
                self.assertEqual(
                    from_language_mock.call_args.kwargs["separators"], ["\n\n"]
                )
