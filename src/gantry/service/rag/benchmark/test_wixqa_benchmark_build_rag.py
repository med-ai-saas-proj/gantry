from __future__ import annotations

from gantry.service.rag.benchmark.test_shared import (
    RagBenchmark,
)
from gantry.service.rag.benchmark.test_wixqa_benchmark_dataloader import (
    WixQaDatasetLoader,
)

import sys
import asyncio


BUILD_RAG_DOCUMENT_BATCH_SIZE: int = 15
BUILD_RAG_CHUNK_SIZE: int = 2000
BUILD_CHUNK_OVERLAP: int = 150

BUILD_TASK_TIMEOUT_SECONDS: int = 1800
BUILD_TASK_POLL_INTERVAL_SECONDS: float = 0.05


async def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    offset = int(arguments[1]) if len(arguments) > 1 else None
    limit = int(arguments[2]) if len(arguments) > 2 else None
    offset = max(0, offset) if offset is not None else None
    limit = max(1, limit) if limit is not None else None

    dataset_loader = WixQaDatasetLoader()
    benchmark = RagBenchmark(dataset_loader)
    # rag_client = build_rag_clients()
    # await benchmark.build_rag_api(
    #     rag_client=rag_client,
    #     offset=offset,
    #     limit=limit,
    #     document_batch_size=BUILD_RAG_DOCUMENT_BATCH_SIZE,
    #     chunk_size=BUILD_RAG_CHUNK_SIZE,
    #     chunk_overlap=BUILD_CHUNK_OVERLAP,
    #     task_timeout_seconds=BUILD_TASK_TIMEOUT_SECONDS,
    #     task_poll_interval_seconds=BUILD_TASK_POLL_INTERVAL_SECONDS,
    # )

    await benchmark.build_rag_direct(
        offset=offset,
        limit=limit,
        document_batch_size=BUILD_RAG_DOCUMENT_BATCH_SIZE,
        chunk_size=BUILD_RAG_CHUNK_SIZE,
        chunk_overlap=BUILD_CHUNK_OVERLAP,
        chunk_splitter="recursive",
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
