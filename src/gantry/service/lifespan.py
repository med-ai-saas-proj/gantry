from gantry.service.rag.factories import getRagService
from gantry.service.file_storage.factories import getFileStorageService

import asyncio


async def rag_embedding_proccess_loop():
    rag_service = getRagService()
    await rag_service.processEmbeddingTask()


async def startup():
    file_storage_service = getFileStorageService()
    file_storage_service.create_bucket_if_not_exists()
    rag_service = getRagService()
    await rag_service.createBucket()
    asyncio.create_task(rag_embedding_proccess_loop())
    pass


async def shutdown():
    # Cleanup code here
    pass
