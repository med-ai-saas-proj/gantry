from gantry.db.session import AsyncSessionManager
from gantry.service.utils.rag.type import (
    IndexParams,
    VectorOpsType,
    VectorIndexType,
    BucketParameters,
    RagEmbeddingRecord,
)
from gantry.service.utils.rag.utils import (
    get_orm_class,
    create_vector_index,
    drop_embedding_table,
    create_embedding_table,
)
from gantry.service.utils.rag.settings import RagSettings
from gantry.management.project.repositories import ProjectRepository
from gantry.service.utils.file_storage.services import FileNotFoundInSystemError
from gantry.shared.custom_types.error_exception import RecoverableError
from gantry.service.utils.file_storage.repositories import FileRepository

import uuid
from typing import Sequence

from pyrusult import Ok, Err, Result
from sqlalchemy import text, select


class BucketNotFoundError(RecoverableError):
    status = 404
    code = "bucket_not_found"
    title = "Bucket not found"
    detail = "The requested bucket was not found in storage."


class RagService:
    def __init__(
        self,
        session_manager: AsyncSessionManager,
        project_repo: ProjectRepository,
        file_repo: FileRepository,
        setting: RagSettings,
    ):
        self.session_manager = session_manager
        self.project_repo = project_repo
        self.file_repo = file_repo
        self.setting = setting

    def getTableName(
        self, dimension: int, index_params: IndexParams, ops_type: VectorOpsType
    ) -> str:
        if index_params["index_type"] == VectorIndexType.hnsw:
            m = (
                index_params["m"]
                if index_params and index_params.get("m")
                else 16
            )
            ef_construction = (
                index_params["ef_construction"]
                if index_params and index_params.get("ef_construction")
                else 64
            )
            return f"rag_{dimension}_hnsw_{ops_type.value}_m{m}_ef{ef_construction}"
        elif index_params["index_type"] == VectorIndexType.ivfflat:
            lists = (
                index_params["lists"]
                if index_params and index_params.get("lists")
                else 100
            )
            return f"rag_{dimension}_ivfflat_{ops_type.value}_lists{lists}"
        else:
            raise ValueError(
                f"Unsupported index type: {index_params['index_type']}"
            )

    def getIndexName(
        self,
        table_name: str,
        index_params: IndexParams,
        ops_type: VectorOpsType,
    ) -> str:
        if index_params["index_type"] == VectorIndexType.hnsw:
            m = (
                index_params["m"]
                if index_params and index_params.get("m")
                else 16
            )
            ef_construction = (
                index_params["ef_construction"]
                if index_params and index_params.get("ef_construction")
                else 64
            )
            return f"idx_{table_name}_embedding_{ops_type.value}_hnsw_m{m}_ef{ef_construction}"
        elif index_params["index_type"] == VectorIndexType.ivfflat:
            lists = (
                index_params["lists"]
                if index_params and index_params.get("lists")
                else 100
            )
            return f"idx_{table_name}_embedding_{ops_type.value}_ivfflat_lists{lists}"
        else:
            raise ValueError(
                f"Unsupported index type: {index_params['index_type']}"
            )

    async def createBucket(
        self,
        dimension: int,
        index_params: IndexParams,
        ops_type: VectorOpsType,
    ):
        async with self.session_manager.get_session() as session:
            table_name = self.getTableName(dimension, index_params, ops_type)
            index_name = self.getIndexName(table_name, index_params, ops_type)
            await create_embedding_table(
                session, table_name, dimension=dimension
            )
            await create_vector_index(
                session, table_name, index_name, ops_type, index_params
            )
            await session.commit()

    async def getConfiguredBuckets(self) -> list[BucketParameters]:
        return self.setting.buckets

    async def addFile(
        self,
        bucket_idx: int,
        file_uid: uuid.UUID,
        project_id: int,
    ) -> Result[None, BucketNotFoundError | FileNotFoundInSystemError]:
        pass

    async def addEmbedding(
        self,
        bucket_idx: int,
        text: str,
        embedding: Sequence[float],
        file_uid: uuid.UUID,
        project_id: int,
    ) -> Result[None, BucketNotFoundError | FileNotFoundInSystemError]:
        async with self.session_manager.get_session() as session:
            file_info = await self.file_repo.getAvailableByUUID(
                session, file_uid, project_id
            )
            if not file_info:
                return Err(FileNotFoundInSystemError())
            buckets = await self.getConfiguredBuckets()
            if not buckets:
                return Err(BucketNotFoundError())
            bucket = buckets[bucket_idx]
            table_name = self.getTableName(
                bucket["dimension"], bucket["index_params"], bucket["ops_type"]
            )

            DynamicBucket = get_orm_class(table_name, len(embedding))
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

    async def getFilesInBucket(
        self,
        bucket_idx: int,
        project_id: int,
    ) -> list[int]:
        async with self.session_manager.get_session() as session:
            buckets = await self.getConfiguredBuckets()
            if not buckets:
                return []
            bucket = buckets[bucket_idx]
            table_name = self.getTableName(
                bucket["dimension"], bucket["index_params"], bucket["ops_type"]
            )
            DynamicBucket = get_orm_class(
                table_name, 0
            )  # dimension is not needed for query
            result = await session.execute(
                select(DynamicBucket.file_id)
                .where(DynamicBucket.project_id == project_id)
                .distinct()
            )
            return list(result.scalars().all())

    async def querySimilar(
        self,
        bucket_idx: int,
        project_id: int,
        embedding: Sequence[float],
        file_uids: Sequence[uuid.UUID] | None = None,
        top_k: int = 5,
    ) -> Sequence[RagEmbeddingRecord]:
        async with self.session_manager.get_session() as session:
            buckets = await self.getConfiguredBuckets()
            if not buckets:
                return []
            bucket = buckets[bucket_idx]
            table_name = self.getTableName(
                bucket["dimension"], bucket["index_params"], bucket["ops_type"]
            )
            DynamicBucket = get_orm_class(table_name, len(embedding))
            if bucket["ops_type"] == VectorOpsType.cosine:
                distance_func = "embedding <=> :embedding"
            elif bucket["ops_type"] == VectorOpsType.l2:
                distance_func = "embedding <-> :embedding"
            elif bucket["ops_type"] == VectorOpsType.ip:
                distance_func = "embedding <#> :embedding"
            else:
                raise ValueError(f"Unsupported ops type: {bucket['ops_type']}")
            stmt = select(DynamicBucket)
            resolved_file_ids: Sequence[int] = []
            if file_uids:
                resolved_file_ids = await self.file_repo.getIdsByUUIDs(
                    session, file_uids, project_id
                )
            if resolved_file_ids:
                stmt = stmt.where(DynamicBucket.file_id.in_(resolved_file_ids))
            stmt = stmt.order_by(text(distance_func)).limit(top_k)
            result = await session.execute(stmt.params(embedding=embedding))
            records: list = []
            for row in result.scalars().all():
                file_model = await self.file_repo.getByKey(session, row.file_id)
                if not file_model:
                    continue
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
                results.append(
                    {
                        "text": record["text"],
                        "embedding": record["embedding"],
                        "created_at": record["created_at"],
                        "file_info": {
                            "uid": file_info_map[record["file_id"]].uuid,
                            "filename": file_info_map[
                                record["file_id"]
                            ].original_filename,
                            "mime_type": file_info_map[
                                record["file_id"]
                            ].mime_type,
                            "size": file_info_map[
                                record["file_id"]
                            ].size_in_bytes,
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
                )
            return records
