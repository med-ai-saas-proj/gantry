from gantry.settings.rag import (
    IndexParams,
    RagParameters,
    VectorOpsType,
    VectorIndexType,
)

from .models import RagData

from typing import cast

from sqlalchemy import Text, Table, Column, Integer, DateTime, text
from sqlalchemy.orm import registry
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.ext.asyncio import AsyncSession


mapper_registry = registry()


def get_orm_class(table_name, dimension) -> type[RagData]:
    table_obj = Table(
        table_name,
        mapper_registry.metadata,
        Column("id", Integer, primary_key=True),
        Column("embedding", VECTOR(dimension)),
        Column("file_id", Integer, nullable=False),
        Column("text", Text, nullable=True),
        Column(
            "created_at", DateTime, nullable=False, server_default=text("NOW()")
        ),
        Column("project_id", Integer, nullable=False),
        Column("lang", Text, nullable=True),
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
    sql = text(f"""
    CREATE TABLE IF NOT EXISTS "Rag"."{table_name}" (
        id BIGSERIAL PRIMARY KEY,
        embedding VECTOR({dimension}),
        file_id BIGINT NOT NULL REFERENCES "FileStorage"."Files"(id) ON DELETE CASCADE,
        project_id BIGINT NOT NULL REFERENCES "Project"."Projects"(id) ON DELETE CASCADE,
        text TEXT,
        lang TEXT default 'simple',
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );""")
    await session.execute(sql)
    sql = text(f"""
    CREATE INDEX IF NOT EXISTS "{table_name}_file_id_idx" ON "Rag"."{table_name}" (file_id);
    """)
    await session.execute(sql)
    sql = text(f"""
    CREATE INDEX IF NOT EXISTS "{table_name}_project_id_idx" ON "Rag"."{table_name}" (project_id);
    """)
    await session.execute(sql)


async def create_bm25_index(
    session: AsyncSession, table_name: str, supported_langs_list: list[str]
):
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
