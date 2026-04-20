from gantry.settings.rag import IndexParams, VectorOpsType, VectorIndexType
from gantry.service.utils.rag.models import RagData

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
        Column("created_at", DateTime),
        Column("updated_at", DateTime),
        Column("project_id", Integer, nullable=False),
        schema="Rag",
    )

    DynamicClass = type(
        f"Dynamic_{table_name}", (object,), {"__table__": table_obj}
    )

    mapper_registry.map_imperatively(DynamicClass, table_obj)
    return cast(type[RagData], DynamicClass)


async def create_embedding_table(
    session: AsyncSession, table_name: str, dimension: int
):
    sql = text(f"""
    CREATE TABLE IF NOT EXISTS "Rag"."{table_name}" (
        id BIGSERIAL PRIMARY KEY,
        embedding VECTOR({dimension}),
        file_id BIGINT NOT NULL REFERENCES "FileStorage"."Files"(id) ON DELETE CASCADE,
        project_id BIGINT NOT NULL REFERENCES "Management"."Projects"(id) ON DELETE CASCADE,
        text TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    );""")
    await session.execute(sql)


async def create_vector_index(
    session: AsyncSession,
    table_name: str,
    index_name: str,
    ops_type: VectorOpsType,
    parms: IndexParams,
):
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


if __name__ == "__main__":
    EmbeddingModel = get_orm_class("user_embeddings_v1", 512)
    new_record = EmbeddingModel(
        embedding=[0.1, 0.2], file_id=123, text="sample text", project_id=0
    )
