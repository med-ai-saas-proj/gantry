"""Unit tests for project DTO validation."""

from gantry.db.factories import getSessionManager
from gantry.settings.rag import VectorOpsType, VectorIndexType
from gantry.service.rag.utils import getTableName, get_orm_class

import unittest


class TestRagInsert(unittest.IsolatedAsyncioTestCase):
    async def test_get_orm_class(self):
        table_name = getTableName(
            {
                "dimension": 1536,
                "index_params": {
                    "index_type": VectorIndexType.hnsw,
                    "m": 16,
                    "ef_construction": 200,
                },
                "ops_type": VectorOpsType.cosine,
            }
        )
        EmbeddingModel = get_orm_class(table_name, 1536)
        async with getSessionManager().get_session() as session:
            new_record = EmbeddingModel(
                embedding=range(1536),
                file_id=0,
                text="sample text",
                project_id=0,
            )
            session.add(new_record)
            await session.commit()


if __name__ == "__main__":
    unittest.main()
