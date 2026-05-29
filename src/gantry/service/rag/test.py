"""Unit tests for project DTO validation."""

from gantry.settings.rag import VectorOpsType, VectorIndexType
from gantry.service.rag.utils import getTableName, get_orm_class

import unittest
from hashlib import sha256

from prometheus_client import h


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
        new_record = EmbeddingModel(
            embedding=range(1536),
            file_id=0,
            text="sample text",
            project_id=0,
            lang="simple",
            chunk_metadata={"key": "value"},
            hash=sha256("sample text".encode()).hexdigest(),
        )

        self.assertEqual(new_record.file_id, 0)
        self.assertEqual(new_record.text, "sample text")
        self.assertEqual(new_record.project_id, 0)
        self.assertEqual(new_record.lang, "simple")


if __name__ == "__main__":
    unittest.main()
