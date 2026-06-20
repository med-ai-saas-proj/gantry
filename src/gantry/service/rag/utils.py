from gantry.settings.rag import (
    IndexParams,
    RagParameters,
    VectorOpsType,
    VectorIndexType,
)

from .models import RagData

from typing import Sequence, TypedDict, cast

import httpx
from sqlalchemy import Text, Table, Column, Integer, DateTime, text
from sqlalchemy.orm import registry
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB


mapper_registry = registry()


def get_orm_class(table_name, dimension) -> type[RagData]:
    table_obj = Table(
        table_name,
        mapper_registry.metadata,
        Column("id", Integer, primary_key=True),
        Column("embedding", VECTOR(dimension)),
        Column("file_id", Integer, nullable=True),
        Column("hash", Text, nullable=False),
        Column("text", Text, nullable=True),
        Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
        ),
        Column("project_id", Integer, nullable=False),
        Column("lang", Text, nullable=True),
        Column("chunk_metadata", JSONB, nullable=True),
        schema="Rag",
        extend_existing=True,
    )

    DynamicClass = type(
        f"Dynamic_{table_name}", (object,), {"__table__": table_obj}
    )

    mapper_registry.map_imperatively(DynamicClass, table_obj)
    return cast(type[RagData], DynamicClass)


db_supported_langs = [
    "simple",
    "arabic",
    "armenian",
    "basque",
    "catalan",
    "danish",
    "dutch",
    "english",
    "finnish",
    "french",
    "german",
    "greek",
    "hindi",
    "hungarian",
    "indonesian",
    "irish",
    "italian",
    "lithuanian",
    "nepali",
    "norwegian",
    "portuguese",
    "romanian",
    "russian",
    "serbian",
    "spanish",
    "swedish",
    "tamil",
    "turkishyiddish",
]


async def create_embedding_table(
    session: AsyncSession, table_name: str, dimension: int
):
    sql = text("CREATE EXTENSION IF NOT EXISTS vector;")
    await session.execute(sql)
    sql = text(f"""
    CREATE TABLE IF NOT EXISTS "Rag"."{table_name}" (
        id BIGSERIAL PRIMARY KEY,
        embedding VECTOR({dimension}),
        file_id BIGINT REFERENCES "FileStorage"."Files"(id) ON DELETE CASCADE,
        hash TEXT NOT NULL,
        project_id BIGINT NOT NULL REFERENCES "Project"."Projects"(id) ON DELETE CASCADE,
        text TEXT,
        chunk_metadata JSONB,
        lang TEXT default 'simple',
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );""")
    await session.execute(sql)
    sql = text(f"""
    ALTER TABLE "Rag"."{table_name}" ADD COLUMN IF NOT EXISTS file_id BIGINT REFERENCES "FileStorage"."Files"(id) ON DELETE CASCADE;
    """)
    await session.execute(sql)
    sql = text(f"""
    ALTER TABLE "Rag"."{table_name}" ADD COLUMN IF NOT EXISTS hash TEXT;
    """)
    await session.execute(sql)
    sql = text(f"""
    ALTER TABLE "Rag"."{table_name}" ADD COLUMN IF NOT EXISTS project_id BIGINT REFERENCES "Project"."Projects"(id) ON DELETE CASCADE;
    """)
    await session.execute(sql)
    sql = text(f"""
    ALTER TABLE "Rag"."{table_name}" ADD COLUMN IF NOT EXISTS text TEXT;
    """)
    await session.execute(sql)
    sql = text(f"""
    ALTER TABLE "Rag"."{table_name}" ADD COLUMN IF NOT EXISTS chunk_metadata JSONB;
    """)
    await session.execute(sql)
    sql = text(f"""
    ALTER TABLE "Rag"."{table_name}" ADD COLUMN IF NOT EXISTS lang TEXT DEFAULT 'simple';
    """)
    await session.execute(sql)
    sql = text(f"""
    ALTER TABLE "Rag"."{table_name}" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
    """)
    await session.execute(sql)
    sql = text(f"""
    UPDATE "Rag"."{table_name}" SET hash = md5(COALESCE(text, '') || ':' || id::text) WHERE hash IS NULL;
    """)
    await session.execute(sql)
    sql = text(f"""
    ALTER TABLE "Rag"."{table_name}" ALTER COLUMN hash SET NOT NULL;
    """)
    await session.execute(sql)
    sql = text(f"""
    CREATE INDEX IF NOT EXISTS "{table_name}_file_id_idx" ON "Rag"."{table_name}" (file_id);
    """)
    await session.execute(sql)
    sql = text(f"""
    CREATE INDEX IF NOT EXISTS "{table_name}_project_id_idx" ON "Rag"."{table_name}" (project_id);
    """)
    await session.execute(sql)
    # Unique partial index on hash for text-only records (file_id IS NULL) per project
    sql = text(f"""
    CREATE UNIQUE INDEX IF NOT EXISTS "{getHashUniqueIndexName(table_name)}" ON "Rag"."{table_name}" (hash, project_id) WHERE file_id IS NULL;
    """)
    await session.execute(sql)


def getHashUniqueIndexName(table_name: str) -> str:
    return f"{table_name}_hash_uq"


async def create_bm25_index(
    session: AsyncSession, table_name: str, supported_langs_list: list[str]
):
    sql = text("CREATE EXTENSION IF NOT EXISTS pg_textsearch;")
    await session.execute(sql)
    db_supported_langs_set = set(db_supported_langs)
    target_langs_set = set(supported_langs_list)
    if not target_langs_set.issubset(db_supported_langs_set):
        unsupported_langs = target_langs_set - db_supported_langs_set
        raise ValueError(
            f"The following languages are not supported by the database: {', '.join(unsupported_langs)}. Supported languages are: {', '.join(db_supported_langs)}"
        )

    for lang in supported_langs_list:
        idx_name = getBm25IndexName(table_name, lang)
        sql = text(f"""
        CREATE INDEX IF NOT EXISTS {idx_name} ON "Rag"."{table_name}" USING bm25 (text)
            WITH (text_config='{lang}') WHERE lang = '{lang}';
        """)
        await session.execute(sql)


async def create_vector_index(
    session: AsyncSession,
    table_name: str,
    rag_store_parameters: RagParameters,
):
    index_name = getIndexName(table_name, rag_store_parameters)
    ops_type = rag_store_parameters["ops_type"]
    parms = rag_store_parameters["index_params"]
    if parms["index_type"] == VectorIndexType.hnsw:
        m = parms["m"] if parms and parms.get("m") else 16
        ef_construction = (
            parms["ef_construction"]
            if parms and parms.get("ef_construction")
            else 64
        )
        sql = text(f"""
            CREATE INDEX IF NOT EXISTS "{index_name}" ON "Rag"."{table_name}" 
            USING hnsw (embedding {ops_type.value}) 
            WITH (m = {m}, ef_construction = {ef_construction});
        """)
    elif parms["index_type"] == VectorIndexType.ivfflat:
        lists = parms["lists"] if parms and parms.get("lists") else 100
        sql = text(f"""
            CREATE INDEX IF NOT EXISTS "{index_name}" ON "Rag"."{table_name}" 
            USING ivfflat (embedding {ops_type.value}) 
            WITH (lists = {lists});
        """)
    else:
        raise ValueError(f"Unsupported index type: {parms['index_type']}")
    await session.execute(sql)


async def drop_embedding_table(session: AsyncSession, table_name: str):
    sql = text(f'DROP TABLE IF EXISTS "Rag"."{table_name}" CASCADE;')
    await session.execute(sql)


def getTableName(rag_store_parameters: RagParameters) -> str:
    dimension = rag_store_parameters["dimension"]
    index_params = rag_store_parameters["index_params"]
    ops_type = rag_store_parameters["ops_type"]
    if index_params["index_type"] == VectorIndexType.hnsw:
        m = index_params["m"] if index_params and index_params.get("m") else 16
        ef_construction = (
            index_params["ef_construction"]
            if index_params and index_params.get("ef_construction")
            else 64
        )
        return f"rag_data_dim{dimension}_hnsw_{ops_type.value}_m{m}_ef{ef_construction}"
    elif index_params["index_type"] == VectorIndexType.ivfflat:
        lists = (
            index_params["lists"]
            if index_params and index_params.get("lists")
            else 100
        )
        return f"rag_data_dim{dimension}_ivfflat_{ops_type.value}_lists{lists}"
    else:
        raise ValueError(
            f"Unsupported index type: {index_params['index_type']}"
        )


def getBm25IndexName(table_name: str, lang: str) -> str:
    return f"{table_name}_{lang}_idx"


def getIndexName(
    table_name: str,
    rag_store_parameters: RagParameters,
) -> str:
    index_params = rag_store_parameters["index_params"]
    ops_type = rag_store_parameters["ops_type"]
    if index_params["index_type"] == VectorIndexType.hnsw:
        m = index_params["m"] if index_params and index_params.get("m") else 16
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
        return (
            f"idx_{table_name}_embedding_{ops_type.value}_ivfflat_lists{lists}"
        )
    else:
        raise ValueError(
            f"Unsupported index type: {index_params['index_type']}"
        )


class RerankApiRequest(TypedDict):
    model: str
    query: str
    documents: Sequence[str]
    top_n: int


class RerankApiResponseItem(TypedDict):
    index: int
    relevance_score: float


class RerankApiResponse(TypedDict):
    results: Sequence[RerankApiResponseItem]


class Reranker:
    def __init__(self, model: str, api_key: str, base_url: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    async def rerankDocuments(
        self, query: str, documents: Sequence[str], top_n: int
    ) -> Sequence[RerankApiResponseItem]:

        data = {
            "query": query,
            "documents": documents,
            "top_n": top_n,
            "return_documents": False,
            "model": self.model,
        }

        async with httpx.AsyncClient(timeout=1200) as client:
            res = await client.post(
                self.base_url.rstrip("/") + "/rerank",
                json=data,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )

            try:
                res.raise_for_status()
            except httpx.HTTPStatusError as e:
                print(f"Server error text: {e.response.text}")
                raise

            res_data = res.json()
            return cast(Sequence[RerankApiResponseItem], res_data["results"])
