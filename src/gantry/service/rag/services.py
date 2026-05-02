from gantry.db import AsyncSessionManager
from gantry.settings.rag import VectorOpsType
from gantry.service.file_storage.types import FileRecord
from gantry.service.file_storage.services import (
    FileStorageService,
    FileNotFoundInSystemError,
)
from gantry.management.project.repositories import ProjectRepository
from gantry.service.file_storage.repositories import FileRepository
from gantry.shared.custom_types.error_exception import (
    RecoverableError,
    InternalServiceError,
)

from .dtos import (
    QueryFilterByFileUid,
    QueryFilterByFileMetadata,
)
from .type import (
    EmbeddingTask,
    ChunkSplitterType,
    RagEmbeddingRecord,
)
from .utils import (
    getIndexName,
    getTableName,
    get_orm_class,
    create_vector_index,
    create_embedding_table,
)
from .models import RagMetadata
from .settings import RagSettings

import io
import re
import csv
import json
import uuid
import importlib
from typing import Sequence, Awaitable, cast

from openai import AsyncOpenAI
from pyrusult import Ok, Err, Result, ResultStatus
from sqlalchemy import func, text, delete, select
from redis.asyncio import Redis
from structlog.stdlib import BoundLogger
from sqlalchemy.dialects.postgresql import insert


class BucketNotFoundError(RecoverableError):
    status = 404
    code = "bucket_not_found"
    title = "Bucket not found"
    detail = "The requested bucket was not found in storage."


class TaskNotFoundError(RecoverableError):
    status = 404
    code = "task_not_found"
    title = "Task not found"
    detail = "The requested task was not found or has expired."


class InvalidEmbeddingDimensionError(RecoverableError):
    status = 400
    code = "invalid_embedding_dimension"
    title = "Invalid embedding dimension"
    detail = "The provided embedding does not match the expected dimension for this bucket."

    def __init__(
        self,
        message: str | None = None,
        from_exception: Exception | None = None,
    ):
        super().__init__(from_exception)
        self.message = message


class RagService:
    def __init__(
        self,
        session_manager: AsyncSessionManager,
        project_repo: ProjectRepository,
        file_repo: FileRepository,
        setting: RagSettings,
        file_storage_service: FileStorageService,
        openai_client: AsyncOpenAI,
        redis: Redis,
        logger: BoundLogger,
    ):
        self.session_manager = session_manager
        self.project_repo = project_repo
        self.file_repo = file_repo
        self.setting = setting
        self.file_storage_service = file_storage_service
        self.openai_client = openai_client
        self.redis = redis
        self.logger = logger

    def _splitByCharacterWindow(
        self,
        text_content: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[str]:
        chunks: list[str] = []
        step = max(1, chunk_size - chunk_overlap)
        for start in range(0, len(text_content), step):
            chunk = text_content[start : start + chunk_size].strip()
            if chunk:
                chunks.append(chunk)
        return chunks

    def _splitByTokenWindow(
        self,
        text_content: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[str]:
        tokens = text_content.split()
        if not tokens:
            return []
        chunks: list[str] = []
        step = max(1, chunk_size - chunk_overlap)
        for start in range(0, len(tokens), step):
            chunk = " ".join(tokens[start : start + chunk_size]).strip()
            if chunk:
                chunks.append(chunk)
        return chunks

    def _splitByRecursiveSeparators(
        self,
        text_content: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[str]:
        paragraphs = [part.strip() for part in text_content.split("\n\n")]
        chunks: list[str] = []
        for paragraph in paragraphs:
            if not paragraph:
                continue
            if len(paragraph) <= chunk_size:
                chunks.append(paragraph)
                continue
            chunks.extend(
                self._splitByCharacterWindow(
                    paragraph,
                    chunk_size,
                    chunk_overlap,
                )
            )
        return chunks

    def _splitByMarkdownSections(
        self,
        text_content: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[str]:
        pattern = re.compile(r"(?m)^#{1,6}\s+")
        starts = [match.start() for match in pattern.finditer(text_content)]
        if not starts:
            return self._splitByRecursiveSeparators(
                text_content,
                chunk_size,
                chunk_overlap,
            )
        starts.append(len(text_content))
        sections: list[str] = []
        for i in range(len(starts) - 1):
            section = text_content[starts[i] : starts[i + 1]].strip()
            if section:
                sections.append(section)
        chunks: list[str] = []
        for section in sections:
            if len(section) <= chunk_size:
                chunks.append(section)
                continue
            chunks.extend(
                self._splitByCharacterWindow(
                    section,
                    chunk_size,
                    chunk_overlap,
                )
            )
        return chunks

    def _splitBySpaCyLikeSentences(
        self,
        text_content: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[str]:
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", text_content)
            if sentence.strip()
        ]
        if not sentences:
            return []
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0
        for sentence in sentences:
            sentence_len = len(sentence)
            if current and current_len + sentence_len > chunk_size:
                chunks.append(" ".join(current))
                if chunk_overlap > 0:
                    overlap_text = " ".join(current)
                    overlap_slice = overlap_text[-chunk_overlap:].strip()
                    current = [overlap_slice] if overlap_slice else []
                    current_len = len(overlap_slice)
                else:
                    current = []
                    current_len = 0
            current.append(sentence)
            current_len += sentence_len + 1
        if current:
            chunks.append(" ".join(current))
        return [chunk for chunk in chunks if chunk.strip()]

    def _splitContent(
        self,
        text_content: str,
        chunk_splitter: ChunkSplitterType,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[str]:
        if chunk_splitter in (
            ChunkSplitterType.simple,
            ChunkSplitterType.character,
        ):
            return self._splitByCharacterWindow(
                text_content,
                chunk_size,
                chunk_overlap,
            )
        if chunk_splitter == ChunkSplitterType.recursive:
            return self._splitByRecursiveSeparators(
                text_content,
                chunk_size,
                chunk_overlap,
            )
        if chunk_splitter == ChunkSplitterType.token:
            return self._splitByTokenWindow(
                text_content,
                chunk_size,
                chunk_overlap,
            )
        if chunk_splitter == ChunkSplitterType.markdown:
            return self._splitByMarkdownSections(
                text_content,
                chunk_size,
                chunk_overlap,
            )
        if chunk_splitter == ChunkSplitterType.paragraph:
            parts = [part.strip() for part in text_content.split("\n\n")]
            return [part for part in parts if part]
        if chunk_splitter == ChunkSplitterType.line:
            parts = [part.strip() for part in text_content.splitlines()]
            return [part for part in parts if part]
        if chunk_splitter == ChunkSplitterType.spacy:
            return self._splitBySpaCyLikeSentences(
                text_content,
                chunk_size,
                chunk_overlap,
            )
        return self._splitByRecursiveSeparators(
            text_content,
            chunk_size,
            chunk_overlap,
        )

    @staticmethod
    def _stringifyTable(
        rows: Sequence[Sequence[object | None]],
    ) -> str:
        serialized_rows: list[str] = []
        for row in rows:
            parts: list[str] = []
            for cell in row:
                parts.append("" if cell is None else str(cell).strip())
            line = "\t".join(parts).strip()
            if line:
                serialized_rows.append(line)
        return "\n".join(serialized_rows).strip()

    def _extractFromPdf(self, content: bytes) -> str:
        pypdf_module = importlib.import_module("pypdf")
        pdf_reader = getattr(pypdf_module, "PdfReader")

        reader = pdf_reader(io.BytesIO(content))
        chunks: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            page_text = page_text.strip()
            if page_text:
                chunks.append(page_text)
        return "\n\n".join(chunks).strip()

    def _extractFromDocx(self, content: bytes) -> str:
        docx_module = importlib.import_module("docx")
        docx_document = getattr(docx_module, "Document")

        document = docx_document(io.BytesIO(content))
        parts: list[str] = []
        for paragraph in document.paragraphs:
            text_part = paragraph.text.strip()
            if text_part:
                parts.append(text_part)
        for table in document.tables:
            table_rows: list[list[object | None]] = []
            for row in table.rows:
                table_rows.append([cell.text.strip() for cell in row.cells])
            table_text = self._stringifyTable(table_rows)
            if table_text:
                parts.append(table_text)
        return "\n\n".join(parts).strip()

    @staticmethod
    def _extractFromDelimitedText(content: bytes, delimiter: str) -> str:
        text_content = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text_content), delimiter=delimiter)
        rows = [row for row in reader]
        return RagService._stringifyTable(rows)

    def _extractFromExcel(self, content: bytes) -> str:
        openpyxl_module = importlib.import_module("openpyxl")
        load_workbook = getattr(openpyxl_module, "load_workbook")

        workbook = load_workbook(
            io.BytesIO(content),
            read_only=True,
            data_only=True,
        )
        sheets: list[str] = []
        for worksheet in workbook.worksheets:
            rows: list[list[object | None]] = []
            for row in worksheet.iter_rows(values_only=True):
                rows.append(list(row))
            table_text = self._stringifyTable(rows)
            if table_text:
                sheets.append(f"# Sheet: {worksheet.title}\n{table_text}")
        return "\n\n".join(sheets).strip()

    @staticmethod
    def _extractFromJson(content: bytes) -> str:
        parsed = json.loads(content.decode("utf-8", errors="ignore"))
        if isinstance(parsed, list):
            return "\n".join(
                json.dumps(item, ensure_ascii=False) for item in parsed
            ).strip()
        if isinstance(parsed, dict):
            return json.dumps(parsed, ensure_ascii=False, indent=2).strip()
        return str(parsed).strip()

    @staticmethod
    def _extractFromJsonLines(content: bytes) -> str:
        lines = content.decode("utf-8", errors="ignore").splitlines()
        parsed_lines: list[str] = []
        for line in lines:
            clean = line.strip()
            if not clean:
                continue
            parsed_lines.append(
                json.dumps(json.loads(clean), ensure_ascii=False)
            )
        return "\n".join(parsed_lines).strip()

    @staticmethod
    def _extractFromParquet(content: bytes) -> str:
        parquet = importlib.import_module("pyarrow.parquet")

        table = parquet.read_table(io.BytesIO(content))
        return "\n".join(
            json.dumps(row, default=str, ensure_ascii=False)
            for row in table.to_pylist()
        ).strip()

    @staticmethod
    def _extractFromFeather(content: bytes) -> str:
        feather = importlib.import_module("pyarrow.feather")

        table = feather.read_table(io.BytesIO(content))
        return "\n".join(
            json.dumps(row, default=str, ensure_ascii=False)
            for row in table.to_pylist()
        ).strip()

    def _extractTextContent(
        self,
        file_info: FileRecord,
        content: bytes,
    ) -> Result[str, InternalServiceError]:
        filename = file_info["filename"].lower()
        mime_type = (file_info.get("mime_type") or "").lower()

        is_pdf = filename.endswith(".pdf") or "application/pdf" in mime_type
        is_docx = (
            filename.endswith(".docx")
            or "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in mime_type
        )
        is_csv = filename.endswith(".csv") or "text/csv" in mime_type
        is_tsv = (
            filename.endswith(".tsv")
            or "text/tab-separated-values" in mime_type
        )
        is_xlsx = (
            filename.endswith(".xlsx")
            or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            in mime_type
        )
        is_json = filename.endswith(".json") or "application/json" in mime_type
        is_jsonl = filename.endswith(".jsonl") or filename.endswith(".ndjson")
        is_parquet = (
            filename.endswith(".parquet")
            or "application/vnd.apache.parquet" in mime_type
        )
        is_feather = filename.endswith(".feather")

        try:
            if is_pdf:
                return Ok(self._extractFromPdf(content))
            if is_docx:
                return Ok(self._extractFromDocx(content))
            if is_csv:
                return Ok(self._extractFromDelimitedText(content, ","))
            if is_tsv:
                return Ok(self._extractFromDelimitedText(content, "\t"))
            if is_xlsx:
                return Ok(self._extractFromExcel(content))
            if is_json:
                return Ok(self._extractFromJson(content))
            if is_jsonl:
                return Ok(self._extractFromJsonLines(content))
            if is_parquet:
                return Ok(self._extractFromParquet(content))
            if is_feather:
                return Ok(self._extractFromFeather(content))
            return Ok(content.decode("utf-8", errors="ignore").strip())
        except Exception as exc:
            return Err(
                InternalServiceError(
                    message=f"Failed to parse file content: {exc}"
                )
            )

    async def createBucket(
        self,
    ):
        async with self.session_manager.get_session() as session:
            table_name = getTableName(self.setting.rag_store_parameters)
            index_name = getIndexName(
                table_name, self.setting.rag_store_parameters
            )
            ops_type = self.setting.rag_store_parameters["ops_type"]
            index_params = self.setting.rag_store_parameters["index_params"]
            dimension = self.setting.rag_store_parameters["dimension"]
            await create_embedding_table(
                session, table_name, dimension=dimension
            )
            await create_vector_index(
                session, table_name, index_name, ops_type, index_params
            )
            await session.commit()

    EMBEDDING_TASK_RETRY_LIMIT = 3
    REDIS_TASK_QUEUE = "rag_embedding_tasks"
    REDIS_TASK_RETRY_HASH = "rag_embedding_task_retries"
    REDIS_TASK_RESULT = "rag_embedding_task_results:{task_id}"
    TASK_TTL = 60 * 60 * 24 * 7

    async def processEmbeddingTask(
        self,
    ):
        while True:
            try:
                await self.processEmbeddingQueue()
            except Exception as exc:
                self.logger.error(
                    f"Error in embedding task processor loop", exc_info=exc
                )
                continue

    async def processEmbeddingQueue(
        self,
    ):
        task = await cast(
            Awaitable[list],
            self.redis.blpop(self.REDIS_TASK_QUEUE, timeout=30),
        )
        if not task:
            return
        task_id = str(task[1])
        result_key = self.REDIS_TASK_RESULT.format(task_id=task_id)

        task_info = await cast(
            Awaitable[str | bytes | None], self.redis.get(result_key)
        )
        if not task_info:
            self.logger.error(
                f"Task with ID {task_id} not found in Redis may have expired or been deleted."
            )
            return
        task_dict = json.loads(task_info)

        try:
            self.logger.info(
                f"Processing embedding task with ID {task_id}",
                task_id=task_id,
                task_info=task_dict,
            )
            (
                await self.processEmbedding(
                    file_uid=uuid.UUID(task_dict["file_uid"]),
                    project_id=task_dict["project_id"],
                    chunk_splitter=ChunkSplitterType(
                        task_dict["chunk_splitter"]
                    ),
                    chunk_size=task_dict["chunk_size"],
                    chunk_overlap=task_dict["chunk_overlap"],
                )
            ).unwrap()
            task_dict["status"] = "completed"
            async with self.redis.pipeline() as pipe:
                await cast(
                    Awaitable[None],
                    pipe.set(
                        result_key, json.dumps(task_dict), ex=self.TASK_TTL
                    ),
                )
                await cast(
                    Awaitable[None],
                    pipe.hdel(self.REDIS_TASK_RETRY_HASH, task_id),
                )
                await pipe.execute()
            self.logger.info(
                f"Successfully processed embedding task with ID {task_id}.",
                task_id=task_id,
                task_info=task_dict,
            )
        except Exception as exc:
            self.logger.error(
                f"Error processing embedding task with ID {task_id}",
                exc_info=exc,
                task_id=task_id,
                task_info=task_dict,
            )
            retry_time = await cast(
                Awaitable[int],
                self.redis.hincrby(self.REDIS_TASK_RETRY_HASH, task_id, 1),
            )
            if int(retry_time) <= self.EMBEDDING_TASK_RETRY_LIMIT:
                self.logger.error(
                    f"Embedding task with ID {task_id} failed on attempt {retry_time}. Retrying...",
                    task_id=task_id,
                    retry_attempt=retry_time,
                    task_info=task_dict,
                    exc_info=exc,
                )
                task_dict["status"] = "failed_and_retrying"
                task_dict["failed_reason"] = str(exc)
                async with self.redis.pipeline() as pipe:
                    await cast(
                        Awaitable[None],
                        pipe.set(
                            result_key, json.dumps(task_dict), ex=self.TASK_TTL
                        ),
                    )
                    await cast(
                        Awaitable[None],
                        pipe.rpush(self.REDIS_TASK_QUEUE, task_id),
                    )
                    await pipe.execute()
            else:
                self.logger.error(
                    f"Embedding task with ID {task_id} has exceeded retry limit.",
                    task_id=task_id,
                    retry_attempt=retry_time,
                    task_info=task_dict,
                )
                task_dict["status"] = "failed_and_dropped"
                task_dict["failed_reason"] = str(exc)
                await cast(
                    Awaitable[None],
                    self.redis.set(
                        result_key, json.dumps(task_dict), ex=self.TASK_TTL
                    ),
                )

    async def processEmbedding(
        self,
        file_uid: uuid.UUID,
        project_id: int,
        chunk_splitter: ChunkSplitterType = ChunkSplitterType.recursive,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
    ) -> Result[
        None,
        BucketNotFoundError
        | FileNotFoundInSystemError
        | InternalServiceError
        | InvalidEmbeddingDimensionError,
    ]:
        res = await self.file_storage_service.getFileInfoAndContent(
            file_uid, project_id
        )
        if res.status == ResultStatus.Err:
            return res.into()
        file_info, content = res.unwrap()

        text_content_res = self._extractTextContent(file_info, content)
        if text_content_res.status == ResultStatus.Err:
            return text_content_res.into()
        text_content = text_content_res.unwrap()
        if not text_content:
            return Ok(None)

        chunks = self._splitContent(
            text_content,
            chunk_splitter,
            chunk_size,
            chunk_overlap,
        )
        if not chunks:
            return Ok(None)

        embedding_response = await self.openai_client.embeddings.create(
            model=self.setting.embedding_model,
            input=chunks,
        )
        embeddings = [item.embedding for item in embedding_response.data]
        if not embeddings:
            return Ok(None)
        if len(embeddings) != len(chunks):
            return Err(
                InternalServiceError(
                    message="Failed to generate embeddings for all chunks."
                )
            )
        target_dimension = self.setting.rag_store_parameters["dimension"]
        table_name = getTableName(self.setting.rag_store_parameters)
        for embedding in embeddings:
            if len(embedding) != target_dimension:
                return Err(
                    InvalidEmbeddingDimensionError(
                        message=f"Generated embedding dimension {len(embedding)} does not match expected dimension {target_dimension}."
                    )
                )

        async with self.session_manager.get_session() as session:
            DynamicBucket = get_orm_class(table_name, target_dimension)

            await session.execute(
                insert(RagMetadata)
                .values(
                    file_id=file_info["id"],
                    project_id=project_id,
                    model_name=self.setting.embedding_model,
                )
                .on_conflict_do_update(
                    index_elements=[
                        RagMetadata.file_id,
                    ],
                    set_={
                        "created_at": func.now(),
                        "model_name": self.setting.embedding_model,
                    },
                )
                .returning(RagMetadata.id)
            )

            await session.execute(
                delete(DynamicBucket).where(
                    DynamicBucket.file_id == file_info["id"],
                    DynamicBucket.project_id == project_id,
                )
            )
            session.add_all(
                [
                    DynamicBucket(
                        embedding=embedding,
                        file_id=file_info["id"],
                        text=chunk.replace("\x00", "").strip(),
                        project_id=project_id,
                    )
                    for chunk, embedding in zip(chunks, embeddings)
                ]
            )
            await session.flush()
            await session.commit()

        return Ok(None)

    async def addFile(
        self,
        file_uid: uuid.UUID,
        project_id: int,
        project_uuid: uuid.UUID,
        chunk_splitter: ChunkSplitterType = ChunkSplitterType.recursive,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
    ) -> Result[str, FileNotFoundInSystemError]:
        task_id = str(uuid.uuid4())
        async with self.session_manager.get_session() as session:
            file_info = await self.file_repo.getAvailableByUUID(
                session, file_uid, project_id
            )
            if not file_info:
                return Err(FileNotFoundInSystemError())

            task_dict = {
                "task_id": task_id,
                "file_id": file_info.id,
                "file_uid": str(file_uid),
                "project_id": project_id,
                "project_uuid": str(project_uuid),
                "chunk_splitter": chunk_splitter.value,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "status": "pending",
            }

        result_key = self.REDIS_TASK_RESULT.format(task_id=task_id)
        async with self.redis.pipeline() as pipe:
            await cast(
                Awaitable[None],
                pipe.set(result_key, json.dumps(task_dict), ex=self.TASK_TTL),
            )
            await cast(
                Awaitable[None], pipe.rpush(self.REDIS_TASK_QUEUE, task_id)
            )
            await pipe.execute()

        return Ok(task_id)

    async def addFileByProjectUid(
        self,
        file_uid: uuid.UUID,
        project_uid: uuid.UUID,
        chunk_splitter: ChunkSplitterType = ChunkSplitterType.recursive,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
    ) -> Result[str, FileNotFoundInSystemError]:
        return await self._wrapProjectUUID(
            project_uid,
            self.addFile,
            file_uid=file_uid,
            project_uuid=project_uid,
            chunk_splitter=chunk_splitter,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    async def getTaskStatus(
        self,
        task_id: str,
        project_id: int,
    ) -> Result[EmbeddingTask, TaskNotFoundError]:
        result_key = self.REDIS_TASK_RESULT.format(task_id=task_id)
        task_info = await cast(
            Awaitable[str | bytes | None], self.redis.get(result_key)
        )
        if not task_info:
            return Err(TaskNotFoundError())

        task_dict = json.loads(task_info)
        if task_dict.get("project_id") != project_id:
            return Err(TaskNotFoundError())

        return Ok(
            EmbeddingTask(
                task_id=task_dict["task_id"],
                file_id=task_dict["file_id"],
                file_uid=uuid.UUID(task_dict["file_uid"]),
                project_id=task_dict["project_id"],
                project_uuid=uuid.UUID(task_dict["project_uuid"]),
                chunk_splitter=ChunkSplitterType(task_dict["chunk_splitter"]),
                chunk_size=task_dict["chunk_size"],
                chunk_overlap=task_dict["chunk_overlap"],
                status=task_dict["status"],
                failed_reason=task_dict.get("failed_reason"),
            )
        )

    async def getTaskStatusByProjectUid(
        self,
        task_id: str,
        project_uid: uuid.UUID,
    ) -> Result[EmbeddingTask, TaskNotFoundError]:
        return await self._wrapProjectUUID(
            project_uid,
            self.getTaskStatus,
            task_id=task_id,
        )

    async def addEmbedding(
        self,
        text: str,
        embedding: Sequence[float],
        file_uid: uuid.UUID,
        project_id: int,
    ) -> Result[
        None,
        BucketNotFoundError
        | FileNotFoundInSystemError
        | InvalidEmbeddingDimensionError,
    ]:
        target_dimension = self.setting.rag_store_parameters["dimension"]
        table_name = getTableName(self.setting.rag_store_parameters)
        if len(embedding) != target_dimension:
            return Err(
                InvalidEmbeddingDimensionError(
                    message=f"Embedding dimension {len(embedding)} does not match expected dimension {target_dimension}."
                )
            )

        async with self.session_manager.get_session() as session:
            file_info = await self.file_repo.getAvailableByUUID(
                session, file_uid, project_id
            )
            if not file_info:
                return Err(FileNotFoundInSystemError())
            DynamicBucket = get_orm_class(table_name, target_dimension)
            new_record = DynamicBucket(
                embedding=embedding,
                file_id=file_info.id,
                text=text,
                project_id=project_id,
            )
            session.add(new_record)
            await session.flush()
            await session.commit()
            return Ok(None)

    async def getFilesInRag(
        self,
        project_id: int,
    ) -> Sequence[FileRecord]:
        async with self.session_manager.get_session() as session:
            result = await session.execute(
                select(RagMetadata.file_id).where(
                    RagMetadata.project_id == project_id
                )
            )
            rows = result.scalars().all()
            file_ids = [row for row in rows]
            files_info = await self.file_repo.getAvailableByIds(
                session, file_ids
            )
            return [
                {
                    "id": file_info.id,
                    "uid": file_info.uuid,
                    "filename": file_info.original_filename,
                    "mime_type": file_info.mime_type,
                    "size": file_info.size_in_bytes,
                    "created_at": file_info.created_at,
                    "extra_metadata": file_info.extra_metadata,
                    "storage_path": file_info.filepath,
                }
                for file_info in files_info
            ]

    async def getFilesInRagByProjectUid(
        self,
        project_uid: uuid.UUID,
    ) -> Sequence[FileRecord]:
        return await self._wrapProjectUUID(
            project_uid,
            self.getFilesInRag,
        )

    async def querySimilarByText(
        self,
        project_id: int,
        query: str,
        filters: QueryFilterByFileMetadata | QueryFilterByFileUid | None = None,
        top_k: int = 5,
        include_embedding: bool = False,
    ) -> Result[
        Sequence[RagEmbeddingRecord],
        FileNotFoundInSystemError
        | InvalidEmbeddingDimensionError
        | InternalServiceError,
    ]:
        embedding_response = await self.openai_client.embeddings.create(
            model=self.setting.embedding_model,
            input=[query],
        )
        if (
            not embedding_response.data
            or not embedding_response.data[0].embedding
        ):
            return Err(
                InternalServiceError(
                    message="Failed to generate embedding for the query."
                )
            )

        query_embedding = embedding_response.data[0].embedding
        return await self.querySimilarByVector(
            project_id=project_id,
            embedding=query_embedding,
            filters=filters,
            top_k=top_k,
            include_embedding=include_embedding,
        )

    async def querySimilarByTextByProjectUid(
        self,
        project_uid: uuid.UUID,
        query: str,
        filters: QueryFilterByFileMetadata | QueryFilterByFileUid | None = None,
        top_k: int = 5,
        include_embedding: bool = False,
    ) -> Result[
        Sequence[RagEmbeddingRecord],
        FileNotFoundInSystemError | InvalidEmbeddingDimensionError,
    ]:
        return await self._wrapProjectUUID(
            project_uid,
            self.querySimilarByText,
            query=query,
            filters=filters,
            top_k=top_k,
            include_embedding=include_embedding,
        )

    async def querySimilarByVector(
        self,
        project_id: int,
        embedding: Sequence[float],
        filters: QueryFilterByFileMetadata | QueryFilterByFileUid | None = None,
        top_k: int = 5,
        include_embedding: bool = False,
    ) -> Result[
        Sequence[RagEmbeddingRecord],
        FileNotFoundInSystemError | InvalidEmbeddingDimensionError,
    ]:
        target_dimension = self.setting.rag_store_parameters["dimension"]
        ops_type = self.setting.rag_store_parameters["ops_type"]
        table_name = getTableName(self.setting.rag_store_parameters)
        if len(embedding) != target_dimension:
            return Err(
                InvalidEmbeddingDimensionError(
                    message=f"Embedding dimension {len(embedding)} does not match expected dimension {target_dimension}."
                )
            )

        async with self.session_manager.get_session() as session:
            DynamicBucket = get_orm_class(table_name, target_dimension)

            if ops_type == VectorOpsType.cosine:
                distance_expr = DynamicBucket.embedding.cosine_distance(
                    embedding
                )
            elif ops_type == VectorOpsType.l2:
                distance_expr = DynamicBucket.embedding.l2_distance(embedding)
            elif ops_type == VectorOpsType.ip:
                distance_expr = DynamicBucket.embedding.max_inner_product(
                    embedding
                )
            else:
                raise ValueError(f"Unsupported ops type: {ops_type}")

            stmt = select(DynamicBucket)
            resolved_file_ids: Sequence[int] | None = None
            if isinstance(filters, QueryFilterByFileUid):
                resolved_files = await self.file_repo.getAvailableIdsByUUIDs(
                    session, filters.file_uids, project_id
                )
                missing_uids = set(filters.file_uids) - set(
                    file_info.uuid for file_info in resolved_files
                )
                if missing_uids:
                    return Err(
                        FileNotFoundInSystemError(
                            message=f"Some file UUIDs not found: {', '.join(str(uid) for uid in missing_uids)}"
                        )
                    )
                resolved_file_ids = [
                    file_info.id for file_info in resolved_files
                ]
            elif isinstance(filters, QueryFilterByFileMetadata):
                resolved_files = await self.file_repo.getAvailableIdsByMetadata(
                    session, filters.file_metadata_filters, project_id
                )
                resolved_file_ids = [
                    file_info.id for file_info in resolved_files
                ]

            if resolved_file_ids is not None:
                stmt = stmt.where(DynamicBucket.file_id.in_(resolved_file_ids))

            # If filters were applied but no files matched, return empty result early to avoid unnecessary distance calculations
            if len(resolved_file_ids or []) == 0:
                return Ok([])

            stmt = stmt.order_by(distance_expr).limit(top_k)
            result = await session.execute(stmt.params(embedding=embedding))
            records: list = []
            for row in result.scalars().all():
                records.append(
                    {
                        "file_id": row.file_id,
                        "text": row.text,
                        "embedding": list(row.embedding),
                        "created_at": row.created_at,
                    }
                )
            file_uids = [record["file_id"] for record in records]
            file_infos = await self.file_repo.getAvailableByIds(
                session, file_uids
            )
            file_info_map = {
                file_info.id: file_info for file_info in file_infos
            }
            results: list[RagEmbeddingRecord] = []
            for record in records:
                data: RagEmbeddingRecord = {
                    "text": record["text"],
                    "created_at": record["created_at"],
                    "embedding": record["embedding"]
                    if include_embedding
                    else [],
                    "file_info": {
                        "id": file_info_map[record["file_id"]].id,
                        "uid": file_info_map[record["file_id"]].uuid,
                        "filename": file_info_map[
                            record["file_id"]
                        ].original_filename,
                        "mime_type": file_info_map[record["file_id"]].mime_type,
                        "size": file_info_map[record["file_id"]].size_in_bytes,
                        "created_at": file_info_map[
                            record["file_id"]
                        ].created_at,
                        "extra_metadata": file_info_map[
                            record["file_id"]
                        ].extra_metadata,
                        "storage_path": file_info_map[
                            record["file_id"]
                        ].filepath,
                    },
                }
                if include_embedding:
                    data["embedding"] = record["embedding"]
                results.append(data)
            return Ok(results)

    async def _wrapProjectUUID(
        self, project_uid: uuid.UUID, async_func, **kwargs
    ):
        async with self.session_manager.get_session() as session:
            project = await self.project_repo.getByUuid(
                session, str(project_uid)
            )
            if not project:
                raise InternalServiceError(
                    message=f"Project with UUID {project_uid} not found."
                )
            project_id = project.id
        return await async_func(project_id=project_id, **kwargs)
